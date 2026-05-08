from .config import ServiceConfigRegistry
from .runtime import Runtime
from typing import Literal
from .schemas import ServiceNotFoundError
from pydantic import BaseModel, ConfigDict, Field



class ServiceStatus(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    # These are required fields
    _name: str
    _status: Literal["on", "off", "starting", "stopping"]
    idle_timeout_seconds: int = Field(min_value=0)

    # These are optional fields
    _last_activity_at: str | None = None
    _seconds_until_sleep: float | None = None

    # Maybe use later
    _healthy: bool | None = None

    # status is mutable
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: Literal["on", "off", "starting", "stopping"]):
        if not value in ["on", "off", "starting", "stopping"]:
            raise ValueError(f"Invalid value for status: {value}")
        self._status = value

    # seconds till sleep is determined automatically
    @property
    def seconds_until_sleep(self):
        if self.status != "on":
            raise AttributeError("Service isnt on, cannot get seconds until sleep")
        
        if self._last_activity_at is None:
            self._seconds_until_sleep = (
                self.idle_timeout_seconds
            )  # On start-up, set to idle timeout
            return float(self._seconds_until_sleep)

        # calculate seconds until sleep based on last activity and idle timeout
        last_activity_time = datetime.fromisoformat(self._last_activity_at)
        time_now = datetime.now()
        seconds_since_last_activity = (time_now - last_activity_time).total_seconds()

        self._seconds_until_sleep = self.idle_timeout_seconds - seconds_since_last_activity
        # If negative, will update poll for activity, if still negative, turn off
        return self._seconds_until_sleep 


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
            timeout_seconds = service.idle_timeout_seconds

            services[name] = ServiceStatus(
                _name=name,
                status=runtime.get_status(service),
                idle_timeout_seconds=timeout_seconds,
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

