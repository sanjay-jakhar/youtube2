"""
Weekly YouTube Analytics checker.
Reads view/watch-time data and logs best-performing content types.
"""

import os
import json
import pickle
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

ANALYTICS_LOG = "output/analytics_log.json"


class AnalyticsChecker:

    def check_weekly(self) -> dict:
        """Pull last 7 days of analytics and log content-type performance."""
        try:
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            from config import Config

            creds = None
            if os.path.exists(Config.YT_TOKEN_FILE):
                with open(Config.YT_TOKEN_FILE, "rb") as f:
                    creds = pickle.load(f)

            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            if not creds or not creds.valid:
                logger.warning("Analytics: no valid credentials")
                return {}

            youtube      = build("youtube", "v3", credentials=creds)
            analytics    = build("youtubeAnalytics", "v2", credentials=creds)

            end_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

            response = analytics.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="views,estimatedMinutesWatched,averageViewDuration,likes",
                dimensions="video",
                sort="-views",
                maxResults=20,
            ).execute()

            rows = response.get("rows", [])
            if not rows:
                logger.info("Analytics: no data for this week yet")
                return {}

            report = {
                "week_ending": end_date,
                "videos": [],
                "summary": {},
            }

            total_views = 0
            for row in rows:
                video_id, views, watch_min, avg_dur, likes = row[0], int(row[1]), float(row[2]), float(row[3]), int(row[4])
                total_views += views

                # Get video title
                vid_resp = youtube.videos().list(part="snippet", id=video_id).execute()
                title = vid_resp["items"][0]["snippet"]["title"] if vid_resp.get("items") else "Unknown"

                report["videos"].append({
                    "video_id":   video_id,
                    "title":      title,
                    "views":      views,
                    "watch_min":  round(watch_min, 1),
                    "avg_dur_s":  round(avg_dur, 1),
                    "likes":      likes,
                })

            report["summary"]["total_views"] = total_views
            report["summary"]["top_video"]   = report["videos"][0]["title"] if report["videos"] else "N/A"

            # Save analytics log
            self._append_log(report)

            logger.info(f"Analytics week {end_date}: {total_views} total views")
            logger.info(f"Top video: {report['summary']['top_video']}")

            for v in report["videos"][:5]:
                logger.info(f"  {v['views']:,} views | {v['avg_dur_s']}s avg | {v['title'][:60]}")

            return report

        except Exception as e:
            logger.error(f"Analytics check failed: {e}")
            return {}

    @staticmethod
    def _append_log(report: dict):
        os.makedirs("output", exist_ok=True)
        existing = []
        if os.path.exists(ANALYTICS_LOG):
            try:
                with open(ANALYTICS_LOG, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.append(report)
        with open(ANALYTICS_LOG, "w", encoding="utf-8") as f:
            json.dump(existing[-52:], f, ensure_ascii=False, indent=2)  # keep 1 year
