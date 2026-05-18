"""
Creates eye-catching YouTube thumbnails with:
  - AI-generated background image
  - Large bold Hindi title in center
  - Colored banner strip behind text
  - Glowing multi-outline text effect
  - Vignette + cinematic color grading
  - Top genre badge + bottom channel tag
"""

import os
import random
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from config import Config

logger = logging.getLogger(__name__)

THUMB_W, THUMB_H = 1280, 720

# Mood → color palette: (banner_color, text_color, glow_color, badge_color)
MOOD_PALETTES = {
    "dark":       ((180, 0,   20),  (255, 255, 255), (255, 60,  60),  (200, 0,   0)),
    "scary":      ((120, 0,   0),   (255, 230, 50),  (255, 80,  0),   (160, 0,   0)),
    "horror":     ((80,  0,   0),   (255, 220, 50),  (255, 50,  0),   (130, 0,   0)),
    "emotional":  ((20,  40,  120), (255, 240, 80),  (255, 200, 0),   (30,  60,  180)),
    "mysterious": ((40,  0,   100), (200, 140, 255), (120, 0,   200), (60,  0,   140)),
    "bright":     ((0,   100, 200), (255, 255, 60),  (0,   200, 255), (0,   140, 255)),
    "action":     ((200, 80,  0),   (255, 255, 255), (255, 160, 0),   (220, 60,  0)),
    "romantic":   ((140, 0,   60),  (255, 200, 220), (255, 100, 160), (180, 0,   80)),
    "universe":   ((0,   20,  80),  (150, 220, 255), (0,   150, 255), (0,   40,  120)),
    "space":      ((0,   10,  50),  (180, 230, 255), (0,   180, 255), (0,   30,  100)),
    "default":    ((20,  20,  20),  (255, 220, 0),   (255, 160, 0),   (60,  60,  60)),
}

# Layout variants — text position and style
LAYOUTS = ["center", "center", "lower_third", "upper_third"]


class ThumbnailCreator:

    def create(
        self,
        story: dict,
        story_id: str,
        base_image_path: str | None = None,
    ) -> str | None:
        mood      = story.get("thumbnail_mood", "default")
        title     = story.get("title", story.get("thumbnail_text", ""))
        palette   = self._pick_palette(mood)
        layout    = random.choice(LAYOUTS)
        genre_tag = story.get("genre", story.get("topic", ""))

        out_path = os.path.join(Config.THUMBS_DIR, f"{story_id}_thumb.jpg")
        os.makedirs(Config.THUMBS_DIR, exist_ok=True)

        # ── 1. Background ─────────────────────────────────────────────────────
        if base_image_path and os.path.exists(base_image_path):
            img = Image.open(base_image_path).convert("RGB")
            img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        else:
            img = self._gradient_bg(palette[0], THUMB_W, THUMB_H)

        # ── 2. Cinematic color grade ──────────────────────────────────────────
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = ImageEnhance.Color(img).enhance(1.4)
        img = ImageEnhance.Brightness(img).enhance(0.80)
        img = ImageEnhance.Sharpness(img).enhance(1.3)

        # ── 3. Vignette ───────────────────────────────────────────────────────
        img = self._add_vignette(img, strength=0.65)

        draw = ImageDraw.Draw(img, "RGBA")

        # ── 4. Text layout ────────────────────────────────────────────────────
        lines = self._wrap_text(title, max_chars=18)
        font_title  = self._load_font(96 if len(lines) <= 2 else 76)
        font_badge  = self._load_font(34)
        font_channel = self._load_font(32)

        if layout == "center":
            text_center_y = THUMB_H // 2
        elif layout == "upper_third":
            text_center_y = THUMB_H // 3
        else:  # lower_third
            text_center_y = THUMB_H * 2 // 3

        line_h   = font_title.size + 16
        block_h  = line_h * len(lines)
        block_top = text_center_y - block_h // 2

        # ── 5. Text banner strip ──────────────────────────────────────────────
        banner_color = (*palette[0], 200)
        pad_v, pad_h = 22, 60
        draw.rounded_rectangle(
            [pad_h // 2, block_top - pad_v,
             THUMB_W - pad_h // 2, block_top + block_h + pad_v],
            radius=18,
            fill=banner_color,
        )

        # ── 6. Title text with glow ───────────────────────────────────────────
        text_color = palette[1]
        glow_color = palette[2]
        for i, line in enumerate(lines):
            y = block_top + i * line_h + line_h // 2
            self._draw_glowing_text(draw, line, font_title, text_color, glow_color,
                                    (THUMB_W // 2, y))

        # ── 7. Top-left genre badge ───────────────────────────────────────────
        if genre_tag:
            badge_text = f"#{genre_tag[:14]}"
            bw = self._text_width(badge_text, font_badge) + 28
            draw.rounded_rectangle([14, 14, 14 + bw, 14 + 48],
                                    radius=10, fill=(*palette[3], 230))
            draw.text((14 + bw // 2, 38), badge_text, font=font_badge,
                      fill=(255, 255, 255, 255), anchor="mm")

        # ── 8. Bottom channel name ─────────────────────────────────────────────
        channel = Config.CHANNEL_NAME[:24]
        draw.rectangle([0, THUMB_H - 52, THUMB_W, THUMB_H],
                       fill=(0, 0, 0, 160))
        draw.text((THUMB_W // 2, THUMB_H - 26), channel, font=font_channel,
                  fill=(220, 220, 220, 255), anchor="mm")

        # ── 9. Accent border ──────────────────────────────────────────────────
        for i, width in enumerate([8, 4, 2]):
            alpha = [120, 180, 255][i]
            draw.rectangle([i * 4, i * 4, THUMB_W - i * 4, THUMB_H - i * 4],
                           outline=(*glow_color, alpha), width=width)

        # ── 10. Corner accents ────────────────────────────────────────────────
        self._draw_corner_accents(draw, glow_color)

        img.convert("RGB").save(out_path, "JPEG", quality=95)
        logger.info(f"Thumbnail saved: {out_path}")
        return out_path

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _pick_palette(mood: str) -> tuple:
        mood = mood.lower()
        for key in MOOD_PALETTES:
            if key in mood:
                return MOOD_PALETTES[key]
        return MOOD_PALETTES["default"]

    @staticmethod
    def _wrap_text(text: str, max_chars: int = 18) -> list[str]:
        words  = text.split()
        lines  = []
        line   = ""
        for w in words:
            if len(line) + len(w) + 1 <= max_chars:
                line = (line + " " + w).strip()
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines[:3]  # max 3 lines

    @staticmethod
    def _text_width(text: str, font) -> int:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    @staticmethod
    def _gradient_bg(color: tuple, w: int, h: int) -> Image.Image:
        import numpy as np
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        c2  = tuple(min(int(c * 1.6), 255) for c in color)
        for y in range(h):
            t = y / h
            arr[y, :] = [
                int(color[0] * (1 - t) + c2[0] * t),
                int(color[1] * (1 - t) + c2[1] * t),
                int(color[2] * (1 - t) + c2[2] * t),
            ]
        return Image.fromarray(arr)

    @staticmethod
    def _add_vignette(img: Image.Image, strength: float = 0.65) -> Image.Image:
        import numpy as np
        w, h   = img.size
        arr    = np.array(img, dtype=np.float32)
        Y, X   = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        dist   = ((X - cx) / (cx * 1.2)) ** 2 + ((Y - cy) / (cy * 1.2)) ** 2
        mask   = 1.0 - np.clip(dist * strength, 0, 1)
        arr   *= mask[:, :, np.newaxis]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    @staticmethod
    def _draw_glowing_text(
        draw, text, font, text_color, glow_color, pos, anchor="mm"
    ):
        x, y = pos
        # Outer glow (large blurry shadow)
        for radius in [12, 8, 5]:
            for dx in range(-radius, radius + 1, 3):
                for dy in range(-radius, radius + 1, 3):
                    if dx * dx + dy * dy <= radius * radius:
                        a = int(100 * (1 - (dx * dx + dy * dy) / (radius * radius + 1)))
                        draw.text((x + dx, y + dy), text, font=font,
                                  fill=(*glow_color, a), anchor=anchor)
        # Dark stroke (outline)
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3),
                       (-4, 0), (4, 0), (0, -4), (0, 4)]:
            draw.text((x + dx, y + dy), text, font=font,
                      fill=(0, 0, 0, 255), anchor=anchor)
        # Main text
        draw.text((x, y), text, font=font, fill=(*text_color, 255), anchor=anchor)

    @staticmethod
    def _draw_corner_accents(draw: ImageDraw.Draw, color: tuple, length: int = 60, width: int = 6):
        c = (*color, 200)
        corners = [
            [(0, length), (0, 0), (length, 0)],
            [(THUMB_W - length, 0), (THUMB_W, 0), (THUMB_W, length)],
            [(0, THUMB_H - length), (0, THUMB_H), (length, THUMB_H)],
            [(THUMB_W - length, THUMB_H), (THUMB_W, THUMB_H), (THUMB_W, THUMB_H - length)],
        ]
        for pts in corners:
            draw.line(pts, fill=c, width=width)

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            os.path.join(Config.FONTS_DIR, "NotoSansDevanagari-Bold.ttf"),
            os.path.join(Config.FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
            os.path.join(Config.FONTS_DIR, "NotoSans-Bold.ttf"),
            os.path.join(Config.FONTS_DIR, "NotoSans-Regular.ttf"),
            # System fonts (Windows)
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\verdanab.ttf",
            r"C:\Windows\Fonts\verdana.ttf",
            # Linux (GitHub Actions)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()
