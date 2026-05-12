import json
import random
import re
import os
import logging
from groq import Groq
from config import Config

logger = logging.getLogger(__name__)

USED_TITLES_FILE = "output/used_titles.json"

class StoryGenerator:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.used_titles = self._load_used_titles()

    # ── Public ─────────────────────────────────────────────────────────────────

    def generate_story(self, genre: str = None, force_short: bool = False) -> dict | None:
        if not genre:
            genre = random.choice(Config.GENRES)

        if force_short:
            target_sec = random.randint(Config.SHORTS_MIN_DURATION, Config.SHORTS_MAX_DURATION)
        else:
            target_sec = random.randint(Config.MIN_DURATION, Config.MAX_DURATION)

        is_short = target_sec < Config.SHORTS_THRESHOLD
        scenes_n = max(2, target_sec // 20) if is_short else max(3, target_sec // 25)

        logger.info(f"Generating {genre} story | {target_sec}s | {'Shorts' if is_short else 'Long'}")

        prompt = self._build_prompt(genre, target_sec, scenes_n)

        try:
            resp = self.client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.92,
                max_tokens=4096,
            )
            raw = resp.choices[0].message.content
            story = self._extract_json(raw)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

        if not story:
            logger.error("Failed to parse story JSON from Groq response")
            return None

        story["genre"]           = genre
        story["is_short"]        = is_short
        story["target_duration"] = target_sec

        self.used_titles.append(story.get("title", ""))
        self._save_used_titles()
        logger.info(f"Story ready: «{story.get('title', '?')}»")
        return story

    # ── Private ────────────────────────────────────────────────────────────────

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a professional Hindi YouTube storyteller and scriptwriter. "
            "You create viral, emotional, cinematic stories that keep viewers glued to the screen. "
            "ALWAYS respond with valid JSON only — no markdown, no code fences, no extra text."
        )

    def _build_prompt(self, genre: str, target_sec: int, scenes_n: int) -> str:
        avoid = ", ".join(self.used_titles[-30:]) if self.used_titles else "None"
        short_note = (
            "This is a YouTube Short (vertical 9:16, under 60s). Make it very fast-paced."
            if target_sec < Config.SHORTS_THRESHOLD
            else "This is a regular YouTube video (horizontal 16:9)."
        )

        # Pick a random story setting/twist to force uniqueness
        settings = [
            "Set in a small Indian village", "Set in a big city like Mumbai or Delhi",
            "Set in a jungle or forest", "Set in a school or college",
            "Set in ancient India", "Set in a hospital",
            "Set during a festival like Diwali or Holi", "Set in a haunted haveli",
            "Set in a desert", "Set during a monsoon night",
            "Set on a train journey", "Set in a poor family's home",
            "Set in future India 2075", "Set in the mountains of Himalayas",
        ]
        twists = [
            "The main character has a shocking secret",
            "Everything was a dream — or was it?",
            "The villain turns out to be the hero's own family member",
            "A supernatural element reveals itself at the end",
            "The hero sacrifices everything for others",
            "A child saves everyone with innocence",
            "An animal plays a key unexpected role",
            "Time reverses or loops",
        ]
        setting = random.choice(settings)
        twist   = random.choice(twists)

        return f"""Create a UNIQUE viral Hindi YouTube {genre} story script. Make it completely different from typical stories.

FORMAT: {short_note}
TARGET DURATION: {target_sec} seconds
SCENES: {scenes_n}
LANGUAGE: Hindi (Devanagari script for all dialogue and narration)
AVOID THESE TITLES (already used): {avoid}
SETTING: {setting}
TWIST IDEA: {twist}

Rules:
- Hook must grab attention in FIRST 5 SECONDS — shock, curiosity, or humor
- Every scene must advance the story — no filler, no boring parts
- Dialogue: fast, punchy, emotional, short sentences (YouTube style)
- Characters must feel REAL with distinct personalities
- End with a memorable twist or emotional punch
- Make it feel like a MOVIE not just a story
- Image prompts must be in English (for AI image generator)
- Be CREATIVE — avoid cliches, make it surprising

Return ONLY this JSON (no markdown, no extra text):
{{
  "title": "Hindi title max 60 chars — viral and emotional",
  "hook": "5-second opening line in Hindi that shocks or intrigues",
  "thumbnail_text": "Max 4 bold Hindi words for thumbnail",
  "thumbnail_mood": "visual mood (dark/bright/emotional/scary/mysterious)",
  "thumbnail_main_color": "dominant color hex like #FF4444",
  "characters": [
    {{
      "name": "Naam",
      "gender": "male",
      "age_group": "young",
      "personality": "brief description",
      "voice_key": "male_young"
    }}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "setting": "Hindi setting description",
      "image_prompt": "Detailed English prompt: cinematic, photorealistic, dramatic lighting, 8K quality, [describe scene vividly]",
      "estimated_duration": 20,
      "narration": "Hindi narrator text",
      "dialogues": [
        {{
          "character": "Naam or NARRATOR",
          "text": "Hindi dialogue",
          "emotion": "scared|happy|sad|angry|excited|mysterious|whispering|crying|normal"
        }}
      ],
      "sfx": "ambient sound keyword (wind/rain/heartbeat/crowd/fire/silence)",
      "music_mood": "suspense|happy|sad|action|peaceful|mysterious|romantic|horror"
    }}
  ],
  "tags": ["hindi kahani", "horror story hindi", "emotional story"],
  "category": "Entertainment"
}}"""

    def _extract_json(self, raw: str) -> dict | None:
        try:
            return json.loads(raw)
        except Exception:
            pass
        # Try to find JSON block in response
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
