"""
YouTube Data API v3 uploader.

First run: call `setup_youtube.py` to complete OAuth — creates youtube_token.json.
Subsequent runs: token is refreshed automatically.
"""

import os
import logging
import pickle
from datetime import datetime, timezone, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import Config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

PRIVACIES = ("public", "unlisted", "private")


class YouTubeUploader:

    def __init__(self):
        self._service = None

    # ── Public ─────────────────────────────────────────────────────────────────

    def upload(
        self,
        video_path: str,
        thumbnail_path: str | None,
        seo: dict,
        story: dict,
        privacy: str = "public",
        schedule_at: datetime | None = None,
    ) -> str | None:
        """
        Upload video. Returns YouTube video ID or None.
        If schedule_at is provided, video is uploaded as private and
        scheduled for that UTC datetime.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        service = self._get_service()
        if not service:
            return None

        # Build snippet
        snippet = {
            "title":        seo["title"],
            "description":  seo["description"],
            "tags":         seo.get("tags", []),
            "categoryId":   seo.get("category_id", "24"),
            "defaultLanguage": seo.get("language", "hi"),
        }

        # Status
        if schedule_at:
            status = {
                "privacyStatus":          "private",
                "publishAt":              schedule_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "selfDeclaredMadeForKids": False,
            }
        else:
            status = {
                "privacyStatus":          privacy,
                "selfDeclaredMadeForKids": False,
            }

        body = {"snippet": snippet, "status": status}

        # Shorts: add #Shorts to title and description
        if seo.get("is_short"):
            body["snippet"]["title"] = seo["title"][:90] + " #Shorts"
            body["snippet"]["description"] = "#Shorts\n" + seo["description"]

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10 MB chunks
        )

        try:
            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )
            video_id = self._resumable_upload(request)
        except HttpError as e:
            logger.error(f"YouTube upload HTTP error: {e}")
            return None

        if not video_id:
            return None

        logger.info(f"Video uploaded: https://youtu.be/{video_id}")

        # Upload thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            self._upload_thumbnail(service, video_id, thumbnail_path)

        return video_id

    def is_authenticated(self) -> bool:
        return self._get_service() is not None

    # ── Private ────────────────────────────────────────────────────────────────

    def _get_service(self):
        if self._service:
            return self._service

        creds = None

        if os.path.exists(Config.YT_TOKEN_FILE):
            with open(Config.YT_TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_token(creds)
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                creds = None

        if not creds or not creds.valid:
            if not os.path.exists(Config.YT_CLIENT_SECRETS):
                logger.error(
                    "client_secrets.json not found. "
                    "Run setup_youtube.py first."
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                Config.YT_CLIENT_SECRETS, SCOPES
            )
            creds = flow.run_local_server(port=0)
            self._save_token(creds)

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    @staticmethod
    def _save_token(creds):
        with open(Config.YT_TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    @staticmethod
    def _resumable_upload(request) -> str | None:
        response = None
        error    = None
        retry    = 0

        while response is None:
            try:
                logger.info(f"Uploading… (retry {retry})")
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info(f"Upload progress: {pct}%")
            except HttpError as e:
                if e.resp.status in (500, 502, 503, 504):
                    error = e
                    retry += 1
                    if retry > 5:
                        logger.error("Max retries exceeded")
                        return None
                    import time; time.sleep(2 ** retry)
                else:
                    raise

        if response:
            return response.get("id")
        return None

    @staticmethod
    def _upload_thumbnail(service, video_id: str, thumb_path: str):
        try:
            service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_path, mimetype="image/jpeg"),
            ).execute()
            logger.info(f"Thumbnail uploaded for {video_id}")
        except HttpError as e:
            logger.warning(f"Thumbnail upload failed: {e}")
