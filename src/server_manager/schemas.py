from pydantic import BaseModel


class ServiceNotFoundError(ValueError):
    pass


class RuntimeCommandError(RuntimeError):
    stderr: str | None = None


class ServiceListResponse(BaseModel):
    content: list[str]
    status: int = 200


class StatusResponse(BaseModel):
    content: str | None
    status: int


class SuccessResponse(BaseModel):
    content: str
    status: int
