from typing import Literal

from .config import ServiceConfigRegistry
from .logging import get_logger
from .runtime import Runtime
from .schemas import ServiceNotFoundError
from .state import StatusManager

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

    async def update_all_statuses(self) -> None:
        for name in self.config_registry.list_services():
            await self.update_status(name)
        logger.info("update_all_statuses | success")

    async def update_status(self, name: str) -> Literal["on", "off", "starting", "stopping"]:
        if name not in self.config_registry.list_services():
            raise ServiceNotFoundError(f"update_status | Service {name} not found")

        service = self.config_registry.get(name)
        updated_status = await self.runtime.get_status(service)
        self.status_manager.set_status(name, updated_status)
        return updated_status

    async def start(self, name: str) -> None:
        if name not in self.config_registry.list_services():
            raise ServiceNotFoundError(f"update_status | Service {name} not found")

        status = self.status_manager.get_status(name)
        if status in ["starting", "stopping"]:
            raise ValueError(
                f"Service {name}: status={status}, cant start until current action is complete"
            )

        service = self.config_registry.get(name)
        await self.runtime.start(service)
        self.status_manager.set_status(name, "starting")

    async def stop(self, name: str) -> None:
        if name not in self.config_registry.list_services():
            raise ServiceNotFoundError(f"update_status | Service {name} not found")

        status = self.status_manager.get_status(name)
        if status in ["starting", "stopping"]:
            raise ValueError(
                f"Service {name}: status={status}, cant stop until current action is complete"
            )

        service = self.config_registry.get(name)
        await self.runtime.stop(service)
        self.status_manager.set_status(name, "stopping")

    async def stop_if_idle(self, name: str) -> None:
        new_status = await self.update_status(name)
        if new_status != "on":
            logger.info(f"stop_if_idle | {name} not on. Aborting")
            return None

        seconds_until_sleep = self.get_seconds_until_sleep(name)
        if seconds_until_sleep < 0:
            # If we are potentially past idle time, we need to check and (if idle) terminate
            logger.info(f"stop_if_idle | {name} confirmed idle, stopping")
            await self.stop(name)

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
        return self.status_manager.get_name_by_status(status_list)

    # Published ServiceConfigRegistryMethods ------------
    def list_services(self) -> list[str]:
        return self.config_registry.list_services()
