"""
AI video generator — animates images into moving character videos.
Priority: MiniMax (HailuoAI) → Kling AI (fal.ai) → HuggingFace SVD (free) → None
"""

import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

MINIMAX_SUBMIT_URL = "https://api.minimax.io/v1/video_generation"
MINIMAX_QUERY_URL  = "https://api.minimax.io/v1/query/video_generation"
MINIMAX_MODEL      = "I2V-01-live"

KLING_MODEL = "fal-ai/kling-video/v1.5/standard/image-to-video"
HF_SVD_URL  = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"


class VideoGenerator:

    def __init__(self):
        self.minimax_key = os.getenv("MINIMAX_KEY", "")
        self.fal_key     = os.getenv("FAL_KEY", "")
        self.hf_token    = os.getenv("HF_TOKEN", "")

        if self.minimax_key:
            logger.info("VideoGenerator: MiniMax (HailuoAI) configured")
        if self.fal_key:
            logger.info("VideoGenerator: Kling AI (fal.ai) configured")
        if self.hf_token:
            logger.info("VideoGenerator: HuggingFace SVD configured (free fallback)")
        if not any([self.minimax_key, self.fal_key, self.hf_token]):
            logger.warning("No video API keys found — animation disabled")

    def animate(
        self,
        image_path: str,
        motion_prompt: str,
        output_path: str,
        duration: int = 5,
    ) -> str | None:
        if self.minimax_key:
            result = self._animate_minimax(image_path, motion_prompt, output_path)
            if result:
                return result
            logger.warning("MiniMax failed, trying next provider...")

        if self.fal_key:
            result = self._animate_kling(image_path, motion_prompt, output_path)
            if result:
                return result
            logger.warning("Kling AI failed, trying HuggingFace SVD...")

        if self.hf_token:
            return self._animate_huggingface(image_path, output_path)

        return None

    # ── MiniMax / HailuoAI ────────────────────────────────────────────────────

    def _animate_minimax(self, image_path: str, motion_prompt: str, output_path: str) -> str | None:
        import base64

        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return None

        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            image_b64 = f"data:image/jpeg;base64,{b64}"

            headers = {
                "Authorization": f"Bearer {self.minimax_key}",
                "Content-Type": "application/json",
            }

            logger.info("MiniMax: submitting video job...")
            resp = requests.post(
                MINIMAX_SUBMIT_URL,
                headers=headers,
                json={
                    "model": MINIMAX_MODEL,
                    "prompt": motion_prompt,
                    "first_frame_image": image_b64,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.error(f"MiniMax submit failed: {resp.status_code} {resp.text[:300]}")
                return None

            data = resp.json()
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code") not in (0, None):
                logger.error(f"MiniMax API error: code={base_resp.get('status_code')} msg={base_resp.get('status_msg')}")
                return None

            task_id = data.get("task_id")
            if not task_id:
                logger.error(f"No task_id in MiniMax response: {data}")
                return None

            logger.info(f"MiniMax task submitted: {task_id}")
            return self._poll_minimax(task_id, headers, output_path)

        except Exception as e:
            logger.error(f"MiniMax animation failed: {e}")
            return None

    def _poll_minimax(self, task_id: str, headers: dict, output_path: str, max_wait: int = 300) -> str | None:
        elapsed  = 0
        interval = 8

        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval

            try:
                resp = requests.get(
                    MINIMAX_QUERY_URL,
                    headers=headers,
                    params={"task_id": task_id},
                    timeout=30,
                )
                data   = resp.json()
                status = data.get("status", "")
                logger.info(f"MiniMax status: {status} ({elapsed}s)")

                if status == "Success":
                    video_url = None
                    for key in ["video_url", "file_url", "url"]:
                        if data.get(key):
                            video_url = data[key]
                            break
                    if not video_url and isinstance(data.get("video"), dict):
                        video_url = data["video"].get("url")
                    if not video_url and data.get("file_id"):
                        video_url = f"https://api.minimax.io/v1/files/{data['file_id']}"

                    if video_url:
                        return self._download(video_url, output_path, headers=headers)
                    logger.error(f"No video URL in response: {data}")
                    return None

                elif status in ("Fail", "Failed", "failed"):
                    logger.error(f"MiniMax job failed: {data}")
                    return None

            except Exception as e:
                logger.warning(f"MiniMax poll error: {e}")

        logger.error("MiniMax video generation timed out")
        return None

    # ── Kling AI via fal.ai ───────────────────────────────────────────────────

    def _animate_kling(self, image_path: str, motion_prompt: str, output_path: str) -> str | None:
        url_file = image_path + ".url"
        if os.path.exists(url_file):
            with open(url_file) as f:
                image_url = f.read().strip()
        else:
            try:
                import fal_client
                image_url = fal_client.upload_file(image_path)
            except Exception as e:
                logger.error(f"Kling upload failed: {e}")
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
                return None
            return self._download(video_url, output_path)
        except Exception as e:
            logger.error(f"Kling animation failed: {e}")
            return None

    # ── HuggingFace SVD (free fallback) ──────────────────────────────────────

    def _animate_huggingface(self, image_path: str, output_path: str) -> str | None:
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            headers = {"Authorization": f"Bearer {self.hf_token}"}

            logger.info("HuggingFace SVD: submitting video job (free tier, may be slow)...")
            resp = requests.post(HF_SVD_URL, headers=headers, data=image_data, timeout=300)

            if resp.status_code == 503:
                logger.warning("HuggingFace model loading — waiting 30s and retrying...")
                time.sleep(30)
                resp = requests.post(HF_SVD_URL, headers=headers, data=image_data, timeout=300)

            if resp.status_code != 200:
                logger.error(f"HuggingFace SVD failed: {resp.status_code} {resp.text[:200]}")
                return None

            content_type = resp.headers.get("Content-Type", "")
            if not any(t in content_type for t in ("video", "octet-stream")):
                logger.error(f"HuggingFace returned unexpected content type: {content_type}")
                return None

            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"HuggingFace SVD video saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"HuggingFace animation failed: {e}")
            return None

    # ── Download helper ───────────────────────────────────────────────────────

    def _download(self, url: str, output_path: str, headers: dict = None) -> str | None:
        try:
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            resp = requests.get(url, headers=headers, timeout=180, stream=True)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Video saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Video download failed: {e}")
            return None
