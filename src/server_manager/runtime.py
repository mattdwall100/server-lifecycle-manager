import asyncio
import json
import subprocess
from pathlib import Path
from typing import Literal

import requests

from .config import ServiceConfig
from .logging import get_LM_settings
from .schemas import RuntimeCommandError

logger = get_LM_settings(__name__)

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
    def __init__(self):
        pass

    async def get_status(
        self, service: ServiceConfig
    ) -> Literal["on", "off", "starting", "stopping"]:
        name = service.name
        container = service.container_name

        # Handling runtime errors
        try:
            state_result = await self.run_subprocess(
                f"docker inspect {container} --format '{{json .State}}'"
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"get_status timed out | service={name}, returned='off'")
            return "off"
        except RuntimeCommandError:
            logger.warning(
                "get_status had non-fatal runtime command error | service={name}, returned='off'"
            )
            # In the future, can use std error to better know whether the program is off or
            # "unknown"/"error" state, These two states would have to be added and handled
            # differently
            return "off"

        # Translating Docker state to internal states
        try:
            state_results = json.loads(state_result.stdout)
        except json.JSONDecodeError as e:
            logger.error("get_status failed | service={service.name}, exception=json.decode")
            raise e

        if state_results.get("Running"):
            return "on"
        elif state_result.get("Status") in {"restarting", "created"}:
            return "starting"
        elif state_result.get("Status") in {"exited", "dead"}:
            return "off"
        else:
            logger.error(f"get_status failed | unknown state_result returned: {str(state_result)}")
            raise ValueError("get_status failed | unknown state_result returned, not handled")

    async def get_activity(self, service: ServiceConfig) -> str:
        response = await requests.get(service.activity_url, timeout=5)
        return response.content

    async def start(self, service: ServiceConfig) -> str:
        compose_path = Path(service.compose_file)
        await self.run_subprocess(f"docker compose -f {compose_path} up -d assistant-server")
        # If no error in running the command, state is now "starting"
        return "starting"

    async def stop(self, service: ServiceConfig):
        compose_path = Path(service.compose_file)
        await self.run_subprocess(f"docker compose -f {compose_path} stop assistant-server")
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
        self, command: str, timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        command_list = command.split(" ")
        kwargs = {"args": command_list, "capture_output": True, "text": True, "timeout": timeout}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                **kwargs,
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"run_subprocess failed | TimeoutExpired command={command}")
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
