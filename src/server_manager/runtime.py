from typing import Literal
import subprocess
from .config import ServiceConfig
import requests
from .logging import get_LM_settings
from .schemas import RuntimeCommandError

logger = get_LM_settings(__name__)


'''Running == true              → "on"
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
        # check if the docker container is running
        # Process the names and return one of Literal[...]
        pass

    def get_activity(self, service: ServiceConfig) -> str:
        response = requests.get(service.activity_url, timeout=5)
        return response.content

    def start(self, service: ServiceConfig):
        # run the start request
        pass

    def stop(self, service: ServiceConfig):
        # run the stop request
        pass

    def run_subprocess(self, command: str, timeout: int) -> subprocess.CompletedProcess[str]:
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

