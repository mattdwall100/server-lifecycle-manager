from pydantic import BaseModel


class ServiceNotFoundError(ValueError): ...


class RuntimeCommandError(RuntimeError):
    def __init__(
        self,
        *args: object,
        stderr: str = "",
    ):
        super().__init__(*args)
        self.stderr = stderr


class ServiceListResponse(BaseModel):
    content: list[str]
    status: int = 200


class StatusResponse(BaseModel):
    content: str | None
    status: int


class SuccessResponse(BaseModel):
    content: str
    status: int
