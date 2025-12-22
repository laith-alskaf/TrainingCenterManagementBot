"""
Post scheduler using APScheduler.
Runs in the same process as the Telegram bot with shared dependency injection.
"""
import logging
from typing import Callable, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from  domain.value_objects import SYRIA_TZ, now_syria, is_past_or_now
from  domain.entities import ScheduledPost, PostStatus, Platform

logger = logging.getLogger(__name__)


class PostScheduler:
    """
    Scheduler for checking and publishing scheduled posts.
    Uses Syria timezone (Asia/Damascus) for all time comparisons.
    """
    
    def __init__(
        self,
        check_interval_minutes: int = 5,
        on_error_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the post scheduler.
        
        Args:
            check_interval_minutes: Interval in minutes to check for posts
            on_error_callback: Async callback function for reporting errors to admin
        """
        self._check_interval = check_interval_minutes
        self._on_error = on_error_callback
        self._scheduler = AsyncIOScheduler(timezone=SYRIA_TZ)
        self._publish_callback: Optional[Callable] = None
    
    def set_publish_callback(self, callback: Callable) -> None:
        """
        Set the callback function for publishing posts.
        This allows the scheduler to use the same use cases as the bot.
        
        Args:
            callback: Async function that takes ScheduledPost and returns bool
        """
        self._publish_callback = callback
    
    async def _check_and_publish(self) -> None:
        """
        Check for pending posts and publish those that are due.
        This is the main job that runs periodically.
        """
        if self._publish_callback is None:
            logger.error("Publish callback not set")
            return
        
        try:
            # The callback should handle fetching and publishing posts
            await self._publish_callback()
        except Exception as e:
            error_msg = f"Scheduler error: {str(e)}"
            logger.error(error_msg)
            if self._on_error:
                try:
                    await self._on_error(error_msg)
                except Exception as notify_error:
                    logger.error(f"Failed to notify admin of scheduler error: {notify_error}")
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        # Add the job to check and publish posts
        self._scheduler.add_job(
            self._check_and_publish,
            trigger=IntervalTrigger(minutes=self._check_interval),
            id="check_posts",
            name="Check and publish scheduled posts",
            replace_existing=True,
        )
        
        self._scheduler.start()
        logger.info(f"Scheduler started, checking every {self._check_interval} minutes (timezone: Asia/Damascus)")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._scheduler.running
    
    async def trigger_check_now(self) -> None:
        """Manually trigger a post check (useful for testing)."""
        await self._check_and_publish()
