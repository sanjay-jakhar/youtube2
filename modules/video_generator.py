"""
AI video generator — animates images into moving character videos via Kling AI (fal.ai).
Uses saved Pollinations URL directly — no re-upload needed.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

KLING_MODEL = "fal-ai/kling-video/v1.5/standard/image-to-video"


class VideoGenerator:

    def __init__(self):
        self.api_key = os.getenv("FAL_KEY", "")
        if self.api_key:
            os.environ["FAL_KEY"] = self.api_key
        else:
            logger.warning("FAL_KEY not set — video animation disabled")

    def animate(
        self,
        image_path: str,
        motion_prompt: str,
        output_path: str,
        duration: int = 5,
    ) -> str | None:
        """
        Animate image with Kling AI. Reads saved Pollinations URL from sidecar
        file (.url) — no upload to fal.ai storage needed.
        """
        if not self.api_key:
            return None

        # Read Pollinations source URL (saved by image_generator)
        url_file = image_path + ".url"
        if os.path.exists(url_file):
            with open(url_file) as f:
                image_url = f.read().strip()
            logger.info(f"Using saved image URL for Kling: {image_url[:80]}...")
        elif os.path.exists(image_path):
            # Fallback: try to upload via fal_client
            try:
                import fal_client
                image_url = fal_client.upload_file(image_path)
                logger.info(f"Uploaded image to fal: {image_url}")
            except Exception as e:
                logger.error(f"Upload fallback failed: {e}")
                return None
        else:
            logger.error(f"Image not found: {image_path}")
            return None

        try:
            import fal_client

            logger.info(f"Kling AI animating: {motion_prompt[:60]}...")
            result = fal_client.run(
                KLING_MODEL,
                arguments={
                    "prompt": motion_prompt,
                    "image_url": image_url,
                    "duration": "5",
                    "aspect_ratio": "9:16",
                },
            )

            video_url = result.get("video", {}).get("url")
            if not video_url:
                logger.error(f"No video URL returned: {result}")
                return None

            return self._download(video_url, output_path)

        except Exception as e:
            logger.error(f"Kling animation failed: {e}")
            return None

    def _download(self, url: str, output_path: str) -> str | None:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            resp = requests.get(url, timeout=180, stream=True)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Animated video saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Video download failed: {e}")
            return None
