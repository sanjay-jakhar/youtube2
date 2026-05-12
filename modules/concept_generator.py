"""
Cinematic video concept generator — no stories, no narration.
Generates viral visual content for YouTube.
"""

import json
import random
import re
import os
import logging
from groq import Groq
from config import Config

logger = logging.getLogger(__name__)

USED_TITLES_FILE = "output/used_titles.json"


class ConceptGenerator:

    def __init__(self):
        self.client      = Groq(api_key=Config.GROQ_API_KEY)
        self.used_titles = self._load_used_titles()

    def generate_concept(self, content_type: str = None, force_short: bool = False) -> dict | None:
        if not content_type:
            content_type = random.choice(Config.CONTENT_TYPES)

        if force_short:
            duration = random.randint(Config.SHORTS_MIN_DURATION, Config.SHORTS_MAX_DURATION)
            is_short = True
            scenes_n = 2
        else:
            duration = random.randint(Config.MIN_DURATION, Config.MAX_DURATION)
            is_short = duration < Config.SHORTS_THRESHOLD
            scenes_n = 2 if is_short else random.randint(4, 7)

        prompt = self._build_prompt(content_type, scenes_n, duration, is_short)

        try:
            resp = self.client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.95,
                max_tokens=3000,
            )
            raw     = resp.choices[0].message.content
            concept = self._extract_json(raw)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

        if not concept:
            logger.error("Failed to parse concept JSON")
            return None

        concept["content_type"]     = content_type
        concept["is_short"]         = is_short
        concept["target_duration"]  = duration
        concept["characters"]       = []   # no characters for cinematic content

        self.used_titles.append(concept.get("title", ""))
        self._save_used_titles()
        logger.info(f"Concept ready: \"{concept.get('title', '?')}\"")
        return concept

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a viral YouTube cinematic video creator. "
            "You create visually stunning, emotionally powerful video concepts "
            "that feel like real movies. NO narration, NO voice-over — pure visuals and sound. "
            "ALWAYS respond with valid JSON only — no markdown, no code fences."
        )

    def _build_prompt(self, content_type: str, scenes_n: int, duration: int, is_short: bool) -> str:
        avoid  = ", ".join(self.used_titles[-30:]) if self.used_titles else "None"
        fmt    = "YouTube Short (9:16 vertical, under 60s, ultra fast-paced)" if is_short else "Regular YouTube video (16:9, cinematic, dramatic)"

        motion_options   = "zoom_in|zoom_out|pan_left|pan_right|tilt_up|tilt_down|parallax|handheld"
        grade_options    = "dark_dramatic|golden_hour|blue_cold|teal_orange|night_glow|warm_fire|deep_ocean|dusty_vintage"
        sfx_options      = "rain|wind|thunder|fire|explosion|crowd|waves|forest|storm|rumble|heartbeat|silence|waterfall|earthquake"
        music_options    = "epic_cinematic|suspense|dramatic_orchestral|dark_ambient|emotional|action_intense|mysterious|horror|peaceful_nature"

        return f"""Create a UNIQUE viral cinematic YouTube video about: {content_type}

FORMAT: {fmt}
DURATION: {duration} seconds total
SCENES: {scenes_n}
AVOID THESE TITLES: {avoid}

RULES:
- NO narration, NO voice-over, NO dialogue unless absolutely necessary
- Pure visuals + ambient sound + music only
- Every scene must look STUNNING and CINEMATIC
- Make it feel like a real movie/documentary
- Title must be in Hindi — dramatic and viral
- Image prompts must describe ultra-realistic, dramatic visual content

Return ONLY this JSON (no markdown):
{{
  "title": "Viral Hindi title — dramatic, emotional, max 70 chars",
  "thumbnail_text": "Max 4 bold Hindi or English words",
  "thumbnail_mood": "dark|bright|emotional|scary|mysterious|dramatic",
  "thumbnail_main_color": "#FF4444",
  "scenes": [
    {{
      "scene_number": 1,
      "image_prompt": "Ultra-detailed English prompt: describe the EXACT visual — what you see, lighting, perspective, atmosphere, scale. Make it jaw-dropping. Example: 'Massive Category 5 hurricane seen from above, swirling clouds, lightning streaks, ocean waves, aerial satellite view, ultra-realistic, 8K'",
      "estimated_duration": 20,
      "motion_type": "{motion_options}",
      "color_grade": "{grade_options}",
      "sfx": "{sfx_options}",
      "music_mood": "{music_options}"
    }}
  ],
  "tags": ["hindi", "viral", "cinematic", "relevant tags here"]
}}"""

    def _extract_json(self, raw: str) -> dict | None:
        try:
            return json.loads(raw)
        except Exception:
            pass
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return None

    def _load_used_titles(self) -> list:
        try:
            with open(USED_TITLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_used_titles(self):
        os.makedirs("output", exist_ok=True)
        with open(USED_TITLES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.used_titles[-500:], f, ensure_ascii=False)
