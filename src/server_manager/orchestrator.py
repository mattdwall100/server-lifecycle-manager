from .runtime import Runtime
from .state import StatusManager
from .config import ServiceConfigRegistry
from .schemas import ServiceNotFoundError
from typing import Literal
from .logging import get_logger

logger = get_logger(__name__)

class Orchestrator:
    def __init__(
        self,
        runtime: Runtime,
        status_manager: StatusManager,
        config_registry: ServiceConfigRegistry,
    ) -> None:
        self.runtime = runtime
        self.status_manager = status_manager
        self.config_registry = config_registry

    def update_status(self, name: str) -> Literal["on", "off", "starting", "stopping"]:
        if name not in self.config_registry.list_services():
            raise ServiceNotFoundError(f"update_status | Service {name} not found")

        updated_status = self.runtime.get_status(name)
        self.status_manager.set_status(name, updated_status)
        return updated_status

    def start(self, name: str) -> None:
        if name not in self.config_registry.list_services():
            raise ServiceNotFoundError(f"update_status | Service {name} not found")

        status = self.status_manager.get_status(name)
        if status in ["starting", "stopping"]:
            raise ValueError(
                f"Service {name} is currently {status}, cannot start until current action is complete"
            )

        self.runtime.start(name)
        self.status_manager.set_status(name, "starting")

    def stop(self, name: str):
        if name not in self.config_registry.list_services():
            raise ServiceNotFoundError(f"update_status | Service {name} not found")

        status = self.status_manager.get_status(name)
        if status in ["starting", "stopping"]:
            raise ValueError(
                f"Service {name} is currently {status}, cannot stop until current action is complete"
            )

        self.runtime.start(name)
        self.status_manager.set_status(name, "stopping")

    def stop_if_idle(self, name: str) -> str:
        new_status = self.update_status(name)
        if new_status != "on":
            logger.info(f"stop_if_idle | {name} not on. Aborting")
            return

        seconds_until_sleep = self.get_seconds_until_sleep(name)
        if seconds_until_sleep < 0:
            # If we are potentially past idle time, we need to check and (if idle) terminate
            logger.info(f"stop_if_idle | {name} confirmed idle, stopping")
            self.stop(name)

        logger.info(f"stop_if_idle | {name} no longer idle")    


    # Published StatusManager Methods -------------------
    def get_status(self, name: str) -> Literal["on", "off", "starting", "stopping"]:
        # We publish this method to other modules that have access to orchestrator
        return self.status_manager.get_status(name)
    
    def get_seconds_until_sleep(self, name: str) -> float:
        return self.status_manager.get_seconds_until_sleep(name)

    def get_name_by_status(
        self, status_list: list[Literal["on", "off", "starting", "stopping"]]
    ) -> list[str]:
        return self.status_manager(status_list)
    
    # Published ServiceConfigRegistryMethods ------------
    def list_services(self) -> list[str]:
        return self.config_registry.list_services()