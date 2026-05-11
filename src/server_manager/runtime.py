import asyncio
import json
import shlex
import subprocess
from typing import Literal

import requests

from .config import ServiceConfig
from .logging import get_logger
from .schemas import RuntimeCommandError

logger = get_logger(__name__)

"""
Get status docker logic:


Running == true              → "on"
Status == "restarting"       → "starting"
Status == "created"          → "starting"
Status == "exited", code 0   → "off"
Status == "exited", code !=0 → "error"
Status == "dead"             → "error"
container missing            → "off"
anything else                → "error" or "unknown"
"""


class Runtime:
    def __init__(self) -> None:
        pass

    async def get_status(
        self, service: ServiceConfig
    ) -> Literal["on", "off", "starting", "stopping"]:
        name = service.name
        container = service.container_name
        mounted_service = service.compose_service

        # Handling runtime errors
        try:
            state_result = await self.run_subprocess(
                'docker inspect --format "{{json .State}}" ' + container,
                cwd=f"/app/{mounted_service}",  # mounting via directory of service via volumes
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"get_status timed out | service={name}, returned='off'")
            return "off"
        except RuntimeCommandError as e:
            for parse_object in ["map has no entry for key", "no such object", "no such container"]:
                if parse_object in e.stderr.lower():
                    logger.warning(
                        f"""get_status had non-fatal runtime error | 
                        service={name}, reason={parse_object}, returned='off'"""
                    )
                    return "off"
            # In the future, can use std error to better know whether the program is off or
            # "unknown"/"error" state, These two states would have to be added and handled
            # differently
            raise e

        # Translating Docker state to internal states
        try:
            loaded_state_result = json.loads(state_result.stdout)
        except json.JSONDecodeError as e:
            logger.error("get_status failed | service={service.name}, exception=json.decode")
            raise e

        if loaded_state_result.get("Running"):
            return "on"
        elif loaded_state_result.get("Status") in {"restarting", "created"}:
            return "starting"
        elif loaded_state_result.get("Status") in {"exited", "dead"}:
            return "off"
        else:
            logger.error(f"get_status failed | unknown state_result returned: {str(state_result)}")
            raise ValueError("get_status failed | unknown state_result returned, not handled")

    async def get_activity(self, service: ServiceConfig, timeout: int = 5) -> str:
        try:
            response = await asyncio.to_thread(
                requests.get, 
                **{"url": service.activity_url, "timeout": timeout}
            )
        except Exception as e:
            # Most likely error is that the app is still starting,
            # So we should change the state back so that it stays as 
            logger.error(f"get_activity failed | name={service.name}, exception={str(e)}")
            raise e from e
        else:
            response_object = response.json()
            return str(response_object["last_activity_time"])

    async def start(self, service: ServiceConfig) -> str:
        mounted_service = service.compose_service

        await self.run_subprocess("docker compose up -d", cwd=f"/app/{mounted_service}")
        # If no error in running the command, state is now "starting"
        return "starting"

    async def stop(self, service: ServiceConfig) -> str:
        mounted_service = service.compose_service
        await self.run_subprocess("docker compose stop", cwd=f"/app/{mounted_service}")

        # If no error in running the command, state is now "stopping"
        if not service.clean_up:
            return "stopping"

        # If we have cleanup commands, run them
        commands = service.clean_up.values()
        for command in commands:
            try:
                await self.run_subprocess(str(command))
            except Exception as e:
                logger.error(f"stop | clean-up failed | command={command}, exception={e}")

        return "stopping"

    async def run_subprocess(
        self, command: str, timeout: int = 30, cwd: str = None
    ) -> subprocess.CompletedProcess[str]:
        command_list = shlex.split(command)
        kwargs = {
            "args": command_list,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "cwd": cwd,
        }
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                **kwargs,
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"run_subprocess failed | TimeoutExpired command={command}")
            raise e
        except Exception as e:
            logger.error(f"run_subprocess failed | command={command} exception={e}")
            raise e

        if result.returncode != 0:
            logger.warning(f"run_subprocess failed | command={command}")
            raise RuntimeCommandError(
                f"Command failed: {command}\n"
                f"Return code: {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}",
                stderr=result.stderr,
            )

        return result
