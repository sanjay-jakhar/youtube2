"""
Creates eye-catching YouTube thumbnails with:
  - AI-generated background image (Pollinations.ai)
  - Bold Hindi text overlay
  - Cinematic vignette + color grading
  - High-contrast border effects
"""

import os
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from config import Config

logger = logging.getLogger(__name__)

THUMB_W, THUMB_H = 1280, 720

# Preset color schemes per mood
MOOD_COLORS = {
    "dark":        {"bg": (10, 5, 20),    "text": (255, 60, 60),   "shadow": (200, 0, 0)},
    "scary":       {"bg": (5, 0, 0),      "text": (255, 30, 30),   "shadow": (180, 0, 0)},
    "emotional":   {"bg": (10, 20, 40),   "text": (255, 220, 80),  "shadow": (200, 140, 0)},
    "mysterious":  {"bg": (15, 10, 30),   "text": (160, 100, 255), "shadow": (80, 0, 180)},
    "bright":      {"bg": (255, 240, 200),"text": (30, 30, 180),   "shadow": (0, 0, 100)},
    "action":      {"bg": (20, 10, 0),    "text": (255, 160, 0),   "shadow": (180, 60, 0)},
    "romantic":    {"bg": (30, 5, 20),    "text": (255, 120, 180), "shadow": (180, 0, 80)},
    "default":     {"bg": (10, 10, 10),   "text": (255, 255, 255), "shadow": (100, 100, 100)},
}


class ThumbnailCreator:

    def create(
        self,
        story: dict,
        story_id: str,
        base_image_path: str | None = None,
    ) -> str | None:
        mood      = story.get("thumbnail_mood", "default")
        text      = story.get("thumbnail_text", story.get("title", "")[:20])
        color_key = self._map_mood(mood)
        colors    = MOOD_COLORS[color_key]

        out_path = os.path.join(Config.THUMBS_DIR, f"{story_id}_thumb.jpg")
        os.makedirs(Config.THUMBS_DIR, exist_ok=True)

        # ── 1. Base image ──────────────────────────────────────────────────────
        if base_image_path and os.path.exists(base_image_path):
            img = Image.open(base_image_path).convert("RGB")
            img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        else:
            img = self._gradient_bg(colors["bg"], THUMB_W, THUMB_H)

        # ── 2. Color grading ───────────────────────────────────────────────────
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Color(img).enhance(1.3)
        img = ImageEnhance.Brightness(img).enhance(0.85)

        # ── 3. Vignette ────────────────────────────────────────────────────────
        img = self._add_vignette(img)

        # ── 4. Dark bottom strip for text readability ──────────────────────────
        draw = ImageDraw.Draw(img, "RGBA")
        strip_h = THUMB_H // 3
        for y in range(THUMB_H - strip_h, THUMB_H):
            alpha = int(200 * ((y - (THUMB_H - strip_h)) / strip_h))
            draw.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0, alpha))

        # ── 5. Main text ───────────────────────────────────────────────────────
        font_large = self._load_font(80)
        font_small = self._load_font(44)

        text_color  = colors["text"]
        shadow_col  = colors["shadow"]

        self._draw_text_with_shadow(
            draw, text, font_large, text_color, shadow_col,
            (THUMB_W // 2, THUMB_H - 120), anchor="mm"
        )

        # Channel name small tag
        channel = Config.CHANNEL_NAME[:20]
        self._draw_text_with_shadow(
            draw, channel, font_small, (200, 200, 200), (0, 0, 0),
            (THUMB_W // 2, THUMB_H - 45), anchor="mm"
        )

        # ── 6. Glowing border ─────────────────────────────────────────────────
        draw.rectangle(
            [4, 4, THUMB_W - 4, THUMB_H - 4],
            outline=(*text_color, 180), width=5
        )

        # ── 7. Save ────────────────────────────────────────────────────────────
        img.convert("RGB").save(out_path, "JPEG", quality=95)
        logger.info(f"Thumbnail saved: {out_path}")
        return out_path

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _map_mood(mood: str) -> str:
        mood = mood.lower()
        for key in MOOD_COLORS:
            if key in mood:
                return key
        return "default"

    @staticmethod
    def _gradient_bg(color: tuple, w: int, h: int) -> Image.Image:
        import numpy as np
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            t = y / h
            r = int(color[0] + (color[0] * 0.3) * t)
            g = int(color[1] + (color[1] * 0.3) * t)
            b = int(color[2] + (color[2] * 0.3) * t)
            arr[y, :] = [min(r, 255), min(g, 255), min(b, 255)]
        return Image.fromarray(arr)

    @staticmethod
    def _add_vignette(img: Image.Image) -> Image.Image:
        import numpy as np
        w, h = img.size
        arr = np.array(img, dtype=np.float32)
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        mask = 1.0 - np.clip(
            ((X - cx) ** 2 / (cx * 1.4) ** 2 + (Y - cy) ** 2 / (cy * 1.4) ** 2),
            0, 1
        )
        arr = arr * mask[:, :, np.newaxis]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    @staticmethod
    def _draw_text_with_shadow(
        draw: ImageDraw.Draw,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: tuple,
        shadow: tuple,
        pos: tuple,
        anchor: str = "mm",
    ):
        x, y = pos
        # Shadow
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
            draw.text((x + dx, y + dy), text, font=font,
                      fill=(*shadow, 220), anchor=anchor)
        # Main text
        draw.text((x, y), text, font=font, fill=(*color, 255), anchor=anchor)

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            os.path.join(Config.FONTS_DIR, "NotoSansDevanagari-Bold.ttf"),
            os.path.join(Config.FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
            os.path.join(Config.FONTS_DIR, "NotoSans-Bold.ttf"),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        # System fallback
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()
