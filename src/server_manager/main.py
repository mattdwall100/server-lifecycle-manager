from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from .api import router
from .config import ServiceConfigRegistry, get_LM_settings
from .logging import get_logger  #
from .monitor import Monitor
from .orchestrator import Orchestrator
from .runtime import Runtime
from .state import StatusManager


def create_app():
    settings = get_LM_settings()
    config_registry = ServiceConfigRegistry._from_yaml(settings.services_config_path)

    runtime = Runtime()

    status_manager = StatusManager.from_runtime_and_config(runtime, config_registry)

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
    async def lifespan(app: FastAPI):
        monitor.start()
        yield
        # await because monitor.stop is an async task and we want it to complete
        await monitor.stop()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.orchestrator = orchestrator

    app.include_router(router)
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
