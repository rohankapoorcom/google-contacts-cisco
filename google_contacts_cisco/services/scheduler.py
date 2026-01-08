"""Background sync scheduler (optional).

This module provides a background scheduler for automatic contact synchronization.
The scheduler runs in a daemon thread and periodically triggers sync operations.
"""

import threading
from typing import Optional

from ..models import SessionLocal
from ..utils.logger import get_logger
from .sync_service import get_sync_service

logger = get_logger(__name__)


class SyncScheduler:
    """Background scheduler for automatic syncs.

    Runs a daemon thread that periodically triggers sync operations
    at a configurable interval. Uses thread-safe sync to prevent
    concurrent sync operations.

    Attributes:
        interval_minutes: Time between sync operations in minutes
        running: Whether the scheduler is currently running
        thread: The background thread running the scheduler
    """

    def __init__(self, interval_minutes: int = 60):
        """Initialize scheduler.

        Args:
            interval_minutes: Sync interval in minutes (default 60)
        """
        self.interval_minutes = interval_minutes
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _run_sync(self) -> None:
        """Run sync task.

        Creates a database session, performs a safe auto sync,
        and handles any errors that occur.
        """
        logger.info("Running scheduled sync")
        db = SessionLocal()
        try:
            sync_service = get_sync_service(db)
            result = sync_service.safe_auto_sync()
            logger.info("Scheduled sync completed: %s", result)
        except Exception as e:
            logger.exception("Scheduled sync failed: %s", e)
        finally:
            db.close()

    def _run_scheduler(self) -> None:
        """Run scheduler loop.

        Continuously runs until stopped, waiting for the configured
        interval between sync operations.
        """
        logger.info(
            "Sync scheduler started (every %d minutes)",
            self.interval_minutes,
        )

        # Convert minutes to seconds for sleep
        interval_seconds = self.interval_minutes * 60

        while self.running:
            # Wait for the interval or until stopped
            if self._stop_event.wait(timeout=interval_seconds):
                # Stop event was set
                break

            if self.running:
                self._run_sync()

    def start(self) -> None:
        """Start background scheduler.

        Creates and starts a daemon thread that runs the scheduler loop.
        Does nothing if the scheduler is already running.
        """
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(
            target=self._run_scheduler,
            daemon=True,
            name="sync-scheduler",
        )
        self.thread.start()
        logger.info("Sync scheduler thread started")

    def stop(self) -> None:
        """Stop background scheduler.

        Signals the scheduler to stop and waits for the thread to finish.
        Does nothing if the scheduler is not running.
        """
        if not self.running:
            logger.warning("Scheduler not running")
            return

        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning("Scheduler thread did not stop cleanly")
        logger.info("Sync scheduler stopped")

    def trigger_immediate_sync(self) -> None:
        """Trigger an immediate sync outside the regular schedule.

        Useful for forcing a sync without waiting for the next scheduled time.
        """
        if not self.running:
            logger.warning("Scheduler not running, cannot trigger immediate sync")
            return

        # Run sync in a separate thread to not block
        threading.Thread(
            target=self._run_sync,
            daemon=True,
            name="sync-immediate",
        ).start()
        logger.info("Triggered immediate sync")


# Global scheduler instance
_scheduler: Optional[SyncScheduler] = None


def get_sync_scheduler() -> Optional[SyncScheduler]:
    """Get the global sync scheduler instance.

    Returns:
        The global SyncScheduler instance, or None if not started
    """
    return _scheduler


def start_sync_scheduler(interval_minutes: int = 60) -> SyncScheduler:
    """Start global sync scheduler.

    Creates and starts the global sync scheduler if not already running.

    Args:
        interval_minutes: Sync interval in minutes (default 60)

    Returns:
        The started SyncScheduler instance
    """
    global _scheduler

    if _scheduler is None:
        _scheduler = SyncScheduler(interval_minutes)
        _scheduler.start()
    elif not _scheduler.running:
        _scheduler = SyncScheduler(interval_minutes)
        _scheduler.start()

    return _scheduler


def stop_sync_scheduler() -> None:
    """Stop global sync scheduler.

    Stops the global scheduler if it's running and clears the reference.
    """
    global _scheduler

    if _scheduler:
        _scheduler.stop()
        _scheduler = None

