"""
Daily upload scheduler — runs the pipeline twice a day at configurable IST times.
"""

import logging
import random
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Config
from modules.pipeline import VideoPipeline
from modules.analytics import AnalyticsChecker

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class DailyScheduler:

    def __init__(self):
        self.scheduler  = BlockingScheduler(timezone=IST)
        self.pipeline   = VideoPipeline()
        self.analytics  = AnalyticsChecker()

    def start(self):
        t1 = Config.UPLOAD_TIME_1.split(":")
        t2 = Config.UPLOAD_TIME_2.split(":")

        # Both uploads are Shorts (under 60s, vertical 9:16)
        self.scheduler.add_job(
            self._run_short_job,
            CronTrigger(hour=int(t1[0]), minute=int(t1[1]), timezone=IST),
            id="upload_morning",
            name="Morning Short upload (IST)",
        )
        self.scheduler.add_job(
            self._run_short_job,
            CronTrigger(hour=int(t2[0]), minute=int(t2[1]), timezone=IST),
            id="upload_evening",
            name="Evening Short upload (IST)",
        )

        # Weekly analytics every Sunday at 10:00 AM IST
        self.scheduler.add_job(
            self._run_analytics,
            CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=IST),
            id="weekly_analytics",
            name="Weekly Analytics Check",
        )

        logger.info("Scheduler started:")
        logger.info(f"  {Config.UPLOAD_TIME_1} IST -- YouTube Short")
        logger.info(f"  {Config.UPLOAD_TIME_2} IST -- YouTube Short")
        logger.info("  Sunday 10:00 AM IST -- Weekly Analytics Check")
        logger.info("Press Ctrl+C to stop.")
        self.scheduler.start()

    def _run_short_job(self):
        content_type = random.choice(Config.CONTENT_TYPES)
        now = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
        logger.info(f"[SHORT] Job at {now} -- {content_type}")
        result = self.pipeline.run(genre=content_type, upload=True, force_short=True)
        if result["status"] == "success":
            logger.info(f"[OK] Short uploaded: {result.get('title')}")
        else:
            logger.error(f"[FAIL] Short failed: {result.get('error')}")

    def _run_long_job(self):
        content_type = random.choice(Config.CONTENT_TYPES)
        now = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
        logger.info(f"[LONG] Job at {now} -- {content_type}")
        result = self.pipeline.run(genre=content_type, upload=True, force_short=False)
        if result["status"] == "success":
            logger.info(f"[OK] Long video uploaded: {result.get('title')}")
        else:
            logger.error(f"[FAIL] Long video failed: {result.get('error')}")

    def _run_analytics(self):
        now = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
        logger.info(f"[ANALYTICS] Weekly check at {now}")
        self.analytics.check_weekly()
