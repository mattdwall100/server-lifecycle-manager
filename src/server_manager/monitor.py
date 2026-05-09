from .orchestrator import Orchestrator
import asyncio
from .logging import get_logger
import contextlib


logger = get_logger(__name__)


class Monitor:
    def __init__(
        self,
        orchestrator: Orchestrator,
        timeout_interval: int = 30,
        check_pending_interval: int = 2,
    ) -> None:
        self.orchestrator = orchestrator
        self.timeout_interval = timeout_interval
        self.check_pending_interval = check_pending_interval

        self._tasks : list[asyncio.Task] = []

    def start(self) -> None:
        # Async background loops
        # start up via threads
        if self._tasks:
            logger.warning(f"start | tasks already exist")

        self._tasks = [
            asyncio.create_task(
                self._timeout_loop(),
                name="timeout-monitor",
            ),
            asyncio.create_task(
                self._check_pending_loop(),
                name="pending-status-monitor",
            ),
        ]
        logger.info("Monitor started")

    async def stop(self) -> None:
        if not self._tasks:
            logger.warning(f"stop | no tasks")

        for task in self._tasks:
            task.cancel()

        for task in self._tasks:
            # Note task.cancel() does so with an error, not silent
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()


    async def _timeout_loop(self):
        # every interval, ask orchestrator what needs to be checked for idleness,

        while True:
            on_services = self.orchestrator.get_name_by_status(["on"])
            for name in on_services:
                seconds_until_sleep = self.orchestrator.get_seconds_until_sleep(name)
                if seconds_until_sleep is not None and seconds_until_sleep < 0:
                    # If we are potentially past idle time, we need to check and (if idle) terminate
                    logger.info(f"Checking for idle | name={name}")
                    try:
                        self.orchestrator.stop_if_idle(name) # Make the awaitable portion await (async runtime) 
                    except Exception as e:
                        logger.error(f"_timeout_loop failed | exception: {e}")

            await asyncio.sleep(self.timeout_interval)

    async def _check_pending_loop(self):
        # every interval, ask orchestrator for services that are starting or stopping, and check their status

        while True:
            pending_service_names = self.orchestrator.get_name_by_status(
                ["starting", "stopping"]
            )
            for name in pending_service_names:
                try:
                    new_status = self.orchestrator.update_status(name)
                except Exception as e:
                    logger.error(f"_check_pending_loop failed | exception: {e}")

                if new_status in ["on", "off"]:
                    logger.info(f"Pending Ended | service={name}, status={new_status}")

            await asyncio.sleep(self.check_pending_interval)


