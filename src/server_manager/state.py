from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import ServiceConfigRegistry
from .logging import get_logger
from .schemas import ServiceNotFoundError

logger = get_logger(__name__)


class ServiceStatus(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    # These are required fields
    name: str
    status_priv: Literal["on", "off", "starting", "stopping"]
    idle_timeout_seconds: int = Field(ge=0)

    # These are optional fields
    last_activity_at: str | None = None
    seconds_until_sleep_priv: float | None = None

    # Maybe use later
    healthy: bool | None = None

    # status is mutable
    @property
    def status(self) -> Literal["on", "off", "starting", "stopping"]:
        return self.status_priv

    @status.setter
    def status(self, value: Literal["on", "off", "starting", "stopping"]) -> None:
        if value not in ["on", "off", "starting", "stopping"]:
            raise ValueError(f"Invalid value for status: {value}")
        self.status_priv = value

    # seconds till sleep is determined automatically
    @property
    def seconds_until_sleep(self) -> float:
        if self.status != "on":
            raise AttributeError("Service isnt on, cannot get seconds until sleep")

        if self.last_activity_at is None:
            self.last_activity_at = str(datetime.now())
            self.seconds_until_sleep_priv = (
                self.idle_timeout_seconds
            )  # On start-up, set to idle timeout
            return float(self.seconds_until_sleep_priv)

        # calculate seconds until sleep based on last activity and idle timeout
        last_activity_time = datetime.fromisoformat(self.last_activity_at)
        time_now = datetime.now()
        seconds_since_last_activity = (time_now - last_activity_time).total_seconds()

        self.seconds_until_sleep_priv = self.idle_timeout_seconds - seconds_since_last_activity
        # If negative, will update poll for activity, if still negative, turn off
        return self.seconds_until_sleep_priv


class StatusManager:
    def __init__(self, services: dict[str, ServiceStatus]):
        self._services = services

    @classmethod
    def from_config(
        cls,
        config_registry: ServiceConfigRegistry,
    ) -> "StatusManager":
        service_list = config_registry.list_services()

        services = {}
        for name in service_list:
            service = config_registry.get(name)
            timeout_seconds = service.idle_timeout_seconds

            services[name] = ServiceStatus(
                name=name,
                status_priv="on",
                idle_timeout_seconds=timeout_seconds,
            )
        logger.info("from_config | Success")
        return cls(services)

    def get_status(self, name: str) -> Literal["on", "off", "starting", "stopping"]:
        if name not in self._services:
            raise ServiceNotFoundError(f"{name} is not a valid service name")

        return self._services[name].status

    def get_seconds_until_sleep(self, name: str) -> float:
        if name not in self._services:
            raise ServiceNotFoundError(f"{name} is not a valid service name")

        return self._services[name].seconds_until_sleep

    def get_name_by_status(
        self, status_list: list[Literal["on", "off", "starting", "stopping"]]
    ) -> list[str]:
        for status in status_list:
            if status not in ["on", "off", "starting", "stopping"]:
                raise ValueError(f"{status} not valid status")
        
        logger.debug(f"get_name_by_status looking | status_list={status_list}")
        found_services = []
        for name, service in self._services.items():
            logger.debug(f"get_name_by_status looking | name={name}, status={service.status}")
            if service.status in status_list:
                print("found")
                found_services.append(name)
        return found_services

    # This we only let orchestrator use
    def set_status(self, name: str, status: Literal["on", "off", "starting", "stopping"]) -> None:
        if name not in self._services:
            raise ServiceNotFoundError(f"{name} is not a valid service name")
        if status not in ["on", "off", "starting", "stopping"]:
            raise ValueError(f"{status} not valid status")

        self._services[name].status = status

    def set_last_activity(self, name: str, last_activity: str) -> None:
        try:
            datetime.fromisoformat(last_activity)
        except Exception as e:
            logger.error(f"set_last_activity failed | last_activity={last_activity}, exception={e}")
            raise e
        self._services[name].last_activity_at=last_activity