"""config.py

Loads environment variables and services.yaml.

 read .env settings
- load services.yaml
- expose service registry
- validate required fields
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import ServiceNotFoundError


class Settings(BaseSettings):
    app_name: str = "Server_Manager"
    api_host: str = Field(default="0.0.0.0", alias="SERVER_MANAGER_HOST")
    api_port: int = Field(default=9000, alias="SERVER_MANAGER_PORT")
    app_env: Literal["dev", "test", "prod"] = Field(default="dev", alias="SERVER_MANAGER_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timeout_interval: int = Field(default=30, alias="TIMEOUT_INTERVAL")
    check_pending_interval: int = Field(default=2, alias="CHECK_PENDING_INTERVAL")

    services_config_path: str = Field(default="config/services.yaml", alias="SERVICES_CONFIG_PATH")
    systemd_configs_path: str = Field(
        default="config/systemd-configs", alias="SERVICES_SYSTEMD_CONFIGS_PATH"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_LM_settings() -> Settings:
    return Settings()


class ServiceConfig(BaseModel):
    name: str
    compose_file: str
    compose_service: str
    container_name: str
    health_url: str | None = None
    activity_url: str = ""
    public_url: str | None = None
    idle_timeout_seconds: int = 600
    enabled: bool = True
    clean_up: dict[str, str] | None = None


class ServiceConfigRegistry:
    def __init__(self, service_configs: dict[str, ServiceConfig]):
        self.__registry = service_configs

    @classmethod
    def _from_yaml(cls, config_path: str) -> "ServiceConfigRegistry":
        """Constructor method to create a ServiceConfigRegistry instance from a YAML file."""
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        raw_services = raw.get("services", {})

        services: dict[str, ServiceConfig] = {}

        for name, config_data in raw_services.items():
            try:
                config_data["name"] = name # Adds name inside config too
                services[name] = ServiceConfig(**config_data)
            except Exception as e:
                raise ValueError(f"Invalid config for service '{name}': {e}") from e

        return cls(services)

    def get(self, name: str) -> ServiceConfig:
        if name not in self.__registry:
            raise ServiceNotFoundError(f"Service {name} not found in config registry")
        else:
            return self.__registry[name]

    def list_services(self) -> list[str]:
        return list(self.__registry.keys())

    def exists(self, name: str) -> bool:
        return name in self.__registry
