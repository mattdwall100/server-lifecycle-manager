import asyncio
import contextlib
import sys

from .logging import get_logger
from .orchestrator import Orchestrator


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

        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        # Async background loops
        # start up via threads
        if self._tasks:
            logger.warning("start | tasks already exist")

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
        logger.info("start | Monitor started")

    async def stop(self) -> None:
        if not self._tasks:
            logger.warning("stop | no tasks")

        logger.warning("stop | Stopping monitor tasks")
        for task in self._tasks:
            task.cancel()

        for task in self._tasks:
            # Note task.cancel() does so with an error, not silent
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

    async def _timeout_loop(self) -> None:
        # every interval, ask orchestrator what needs to be checked for idleness,

        while True:
            on_services = self.orchestrator.get_name_by_status(["on"])
            for name in on_services:
                seconds_until_sleep = self.orchestrator.get_seconds_until_sleep(name)
                if seconds_until_sleep is not None and seconds_until_sleep < 0:
                    # If we are potentially past idle time, we need to check and (if idle) terminate
                    logger.info(f"_timeout_loop checking idle | name={name}")
                    try:
                        await self.orchestrator.stop_if_idle(
                            name
                        )  # Make the awaitable portion await (async runtime)
                    except Exception as e:
                        logger.error(f"_timeout_loop failed | exception: {e}")

            await asyncio.sleep(self.timeout_interval)

    async def _check_pending_loop(self) -> None:
        # every interval, ask orchestrator for starting/stopping services and check status

        while True:
            pending_service_names = self.orchestrator.get_name_by_status(["starting", "stopping"])
            for name in pending_service_names:
                old_status = self.orchestrator.get_status(name)

                logger.info(f"_check_pending_loop checking | name={name}")
                try:
                    new_status = await self.orchestrator.update_status(name)
                    logger.info(f"_check_pending_loop checked | name={name}, state={new_status}")
                except Exception as e:
                    logger.error(f"_check_pending_loop failed | exception: {e}")

                if new_status == "on": # If "on", we need to make sure active
                    # Once start has succeeded, update its activity, redo if cant reach
                    try:
                        await self.orchestrator.update_last_activity(name)
                    except Exception as e:
                        if "emote end closed connection without response" in str(e).lower(): 
                            logger.info(f"_check_pending_loop ClosedConnectionError | /activity not yet open, name={name}, exc={e}")
                            self.orchestrator.set_status(name, old_status) # redo loop
                        elif "connection refused" in str(e).lower():
                            logger.info(f"_check_pending_loop ConnectionError | /activity not yet open, name={name}")
                            self.orchestrator.set_status(name, old_status) # redo loop
                        else:
                            logger.error(f"_check_pending_loop failed | unknown name={name}, exc={e}")
                            sys.exit()
                    else:     
                        logger.info(f"_check_pending_loop success | service={name}, status={new_status}")
                
                # other statuses are handled accordingly (off: show state, still pending: check state again)

            await asyncio.sleep(self.check_pending_interval)
