from typing import Literal
import subprocess
from .config import ServiceConfig
import requests
from .logging import get_LM_settings
from .schemas import RuntimeCommandError
from pathlib import Path
import json

logger = get_LM_settings(__name__)

'''
Get status docker logic:


Running == true              → "on"
Status == "restarting"       → "starting"
Status == "created"          → "starting"
Status == "exited", code 0   → "off"
Status == "exited", code !=0 → "error"
Status == "dead"             → "error"
container missing            → "off"
anything else                → "error" or "unknown"
'''




class Runtime:
    def __init__(self):
        self.result_status_map = {

        }

    def get_status(self, service: ServiceConfig) -> Literal["on", "off", "starting", "stopping"]:
        name = service.name
        container = service.container_name

        # Handling runtime errors
        try:
            state_result = self.run_subprocess(f"docker inspect {container} --format '{{json .State}}'")
        except subprocess.TimeoutExpired as e:
            logger.warning("get_status timed out | service={name}, returned='off'")
            return "off"
        except RuntimeCommandError as e:
            logger.warning("get_status had non-fatal runtime command error | service={name}, returned='off'")
            # In the future, can use std error to better know whether the program is off or "unknown"/"error" state,
            # These two states would have to be added and handled differently
            return "off"
        
        # Translating Docker state to internal states
        try:
            state_results = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error("get_status failed | service={service.name}, exception=json.decode")
            raise e
        
        if state_results.get("Running") == True:
            return "on"
        elif state_result.get("Status") in {"restarting", "created"}:
            return "starting"
        elif state_result.get("Status") in {"exited", "dead"}:
            return "off"
        else:
            logger.error(f"get_status failed | unknown state_result returned: {str(state_result)}")
            raise ValueError(f"get_status failed | unknown state_result returned, not handled")

    def get_activity(self, service: ServiceConfig) -> str:
        response = requests.get(service.activity_url, timeout=5)
        return response.content

    def start(self, service: ServiceConfig) -> str:
        compose_path = Path(service.compose_file)
        self.run_subprocess(f"docker compose -f {compose_path} up -d assistant-server")
        # If no error in running the command, state is now "starting"
        return "starting"

    def stop(self, service: ServiceConfig):
        compose_path = Path(service.compose_file)
        self.run_subprocess(f"docker compose -f {compose_path} stop assistant-server")
        # If no error in running the command, state is now "stopping"
        return "stopping"
    
    def run_subprocess(self, command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        command_list = command.split(" ")
        try:
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                timeout=timeout,
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
                stderr=result.stderr
            )

        return result

