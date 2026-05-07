from .schemas import ServiceStatus
from .config import ServiceConfigRegistry
from .runtime import Runtime
from typing import Literal
from .schemas import ServiceNotFoundError


class StatusManager:
    def __init__(self, services: dict[str, ServiceStatus]):
        self._services = services

    @classmethod
    def from_runtime_and_config(
        cls,
        runtime: Runtime,
        config_registry: ServiceConfigRegistry,
    ) -> "StatusManager":
        service_list = config_registry.list_services()

        services = {}
        for name in service_list:
            service = config_registry.get(name)
            timeout_seconds = service.timeout_seconds

            services[name] = ServiceStatus(
                _name=name,
                status=runtime.get_status(service),
                _idle_timeout_seconds=timeout_seconds,
            )

        return cls(services)

    def get_status(self, name: str) -> Literal["on", "off", "starting", "stopping"]:
        if name not in self.services:
            raise ServiceNotFoundError(f"{name} is not a valid service name")
        
        return self._services[name].status
    
    def get_seconds_until_sleep(self, name: str) -> float:
        if name not in self.services:
            raise ServiceNotFoundError(f"{name} is not a valid service name")
        
        return self._services[name].seconds_until_sleep

    def get_name_by_status(
        self, status_list: list[Literal["on", "off", "starting", "stopping"]]
    ) -> list[str]:
        for status in status_list:
            if status not in ['on', 'off', 'starting', 'stopping']:
                raise ValueError(f"{status} not valid status")

        found_services = []
        for name, service in self._services.items():
            if service.status in status_list:
                found_services.append(name)
        return found_services

    # This we only let orchestrator use
    def set_status(self, name: str, status: Literal["on", "off", "starting", "stopping"]) -> None:
        if name not in self.services:
            raise ServiceNotFoundError(f"{name} is not a valid service name")
        if status not in ['on', 'off', 'starting', 'stopping']:
            raise ValueError(f"{status} not valid status")
            
        self._services[name].status = status

