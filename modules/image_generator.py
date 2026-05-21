import os
import time
import random
import logging
import requests
from urllib.parse import quote
from config import Config

logger = logging.getLogger(__name__)

# Different visual styles — randomly picked per scene for variety
VISUAL_STYLES = [
    ", cinematic photography, dramatic lighting, 8K, photorealistic, ultra detailed",
    ", anime style, vibrant colors, dramatic scene, highly detailed, Studio Ghibli inspired",
    ", digital painting, concept art, vivid colors, cinematic composition, trending on ArtStation",
    ", dark fantasy art, dramatic shadows, moody atmosphere, ultra detailed, cinematic",
    ", comic book style, bold colors, dynamic composition, highly detailed illustration",
    ", oil painting style, rich textures, dramatic lighting, masterpiece quality",
    ", watercolor illustration, soft beautiful colors, hand-painted, detailed, cinematic",
    ", 3D render, Pixar style, vibrant expressive, detailed environment, cinematic lighting",
    ", cinematic still, golden hour lighting, ultra sharp, 8K DSLR, professional film",
    ", storybook illustration, warm colors, detailed, beautiful, emotional scene",
]


class ImageGenerator:
    """Generates scene images using Pollinations.ai (completely free, no API key)."""

    def generate_scene_image(
        self,
        prompt: str,
        scene_idx: int,
        story_id: str,
        is_short: bool = False,
        retries: int = 3,
    ) -> str | None:
        out_dir = os.path.join(Config.IMAGES_DIR, story_id)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"scene_{scene_idx:02d}.jpg")

        if is_short:
            w, h = 1080, 1920
        else:
            w, h = Config.IMAGE_WIDTH, Config.IMAGE_HEIGHT

        seed = random.randint(10000, 99999)
        style_suffix = random.choice(VISUAL_STYLES)
        full_prompt = prompt + style_suffix
        url = (
            f"{Config.POLLINATIONS_URL}/{quote(full_prompt)}"
            f"?width={w}&height={h}&nologo=true&model=flux&seed={seed}"
        )

        for attempt in range(retries):
            try:
                logger.info(f"Fetching scene {scene_idx} image (attempt {attempt+1})")
                resp = requests.get(url, timeout=90)
                resp.raise_for_status()
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Scene image saved: {out_path}")
                # Save source URL alongside image for Kling AI to use directly
                with open(out_path + ".url", "w") as f:
                    f.write(url)
                return out_path
            except Exception as e:
                logger.warning(f"Image attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))

        # Last-resort fallback: solid gradient image
        return self._fallback_image(out_path, w, h, scene_idx)

    def generate_thumbnail_image(
        self,
        prompt: str,
        story_id: str,
        mood: str = "dramatic",
        retries: int = 3,
    ) -> str | None:
        out_dir = os.path.join(Config.IMAGES_DIR, story_id)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "thumbnail_base.jpg")

        thumb_prompt = (
            f"{prompt}, {mood}, extreme close-up face with intense emotion, "
            "cinematic, dramatic lighting, thumbnail style, 4K"
        )
        url = (
            f"{Config.POLLINATIONS_URL}/{quote(thumb_prompt)}"
            f"?width=1280&height=720&nologo=true&model=flux"
        )

        for attempt in range(retries):
            try:
                resp = requests.get(url, timeout=90)
                resp.raise_for_status()
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                return out_path
            except Exception as e:
                logger.warning(f"Thumbnail image attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))

        return self._fallback_image(out_path, 1280, 720, 0)

    @staticmethod
    def _fallback_image(path: str, w: int, h: int, idx: int) -> str:
        """Create a simple gradient image when download fails."""
        from PIL import Image
        import numpy as np

        colors = [
            [(20, 20, 60), (80, 20, 20)],   # dark blue → dark red
            [(10, 40, 10), (60, 60, 10)],   # dark green → olive
            [(40, 10, 40), (20, 20, 80)],   # purple → navy
        ]
        pair = colors[idx % len(colors)]
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            t = y / h
            r = int(pair[0][0] * (1 - t) + pair[1][0] * t)
            g = int(pair[0][1] * (1 - t) + pair[1][1] * t)
            b = int(pair[0][2] * (1 - t) + pair[1][2] * t)
            arr[y, :] = [r, g, b]

        Image.fromarray(arr).save(path)
        logger.info(f"Fallback gradient image saved: {path}")
        return path
