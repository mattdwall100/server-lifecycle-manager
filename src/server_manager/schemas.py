from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from datetime import datetime


class ServiceConfig(BaseModel):
    display_name: str
    compose_file: str
    compose_service: str
    container_name: str
    health_url: str | None = None
    activity_url: str | None = None
    public_url: str | None = None
    idle_timeout_seconds: int = 600
    enabled: bool = True


class ServiceStatus(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    # These are required fields
    _name: str
    _status: Literal["on", "off", "starting", "stopping"]
    _idle_timeout_seconds: int = Field(min_value=0)

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
                self._idle_timeout_seconds
            )  # On start-up, set to idle timeout
            return float(self._seconds_until_sleep)

        # calculate seconds until sleep based on last activity and idle timeout
        last_activity_time = datetime.fromisoformat(self._last_activity_at)
        time_now = datetime.now()
        seconds_since_last_activity = (time_now - last_activity_time).total_seconds()

        self._seconds_until_sleep = self._idle_timeout_seconds - seconds_since_last_activity
        # If negative, will update poll for activity, if still negative, turn off
        return self._seconds_until_sleep 


class ServiceNotFoundError(ValueError):
    pass


class ServiceListResponse(BaseModel):
    content: list[str]
    status: int = 200

class StatusResponse(BaseModel):
    content: str | None
    status: int

class SuccessResponse(BaseModel):
    content: str
    status: int
