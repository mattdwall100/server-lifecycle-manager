from typing import Literal

from .schemas import ServiceConfig
import requests


class Runtime:
    def __init__(self):
        pass

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
