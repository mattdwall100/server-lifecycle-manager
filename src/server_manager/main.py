from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI

from .api import router
from .config import ServiceConfigRegistry, get_LM_settings
from .logging import get_logger  #
from .monitor import Monitor
from .orchestrator import Orchestrator
from .runtime import Runtime
from .state import StatusManager


def create_app() -> FastAPI:
    settings = get_LM_settings()
    config_registry = ServiceConfigRegistry._from_yaml(settings.services_config_path)
    get_logger(__name__).info("_from_yaml | ServiceConfigRegistry create successfully from yaml")

    runtime = Runtime()

    # Note that the runtime is async, uvicorn doesnt support it.
    # So we start by providing all statuses "on" status, and update them in the app lifespan.
    status_manager = StatusManager.from_config(config_registry)

    orchestrator = Orchestrator(
        runtime=runtime,
        status_manager=status_manager,
        config_registry=config_registry,
    )

    monitor = Monitor(
        orchestrator=orchestrator,
        timeout_interval=settings.timeout_interval,
        check_pending_interval=settings.check_pending_interval,
    )

    # Asynchronous custom context manager is a param for fastapi app for start and end tasks
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:
        await orchestrator.update_all_statuses()
        status_string = ""
        for service in config_registry.list_services():
            status_string += f"{service}={status_manager.get_status(service)}, "
        get_logger(__name__).info(f"create_app | current statuses: {status_string}")

        monitor.start()

        yield
        # await because monitor.stop is an async task and we want it to complete
        await monitor.stop()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.orchestrator = orchestrator

    app.include_router(router)
    get_logger(__name__).info("create_app | fastapi app created successfully")
    return app


if __name__ == "__main__":
    get_logger(__name__).info("Starting assistant server...")

    settings = get_LM_settings()
    # app = create_app(settings)

    uvicorn.run(
        "src.server_manager.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "dev",
        log_level=settings.log_level.lower(),
    )
