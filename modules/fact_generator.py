"""
Fact video generator — generates interesting Hindi facts with cinematic visuals.
Female voice narrates facts over stunning background visuals.
"""

import json
import random
import re
import os
import logging
from groq import Groq
from config import Config

logger = logging.getLogger(__name__)

USED_TITLES_FILE  = "output/used_titles.json"
USED_TOPICS_FILE  = "output/used_topics.json"

FACT_TOPICS = [
    "universe and space",
    "deep ocean secrets",
    "human body amazing facts",
    "ancient India history",
    "dangerous animals",
    "mind-blowing science",
    "earth and nature",
    "technology and AI future",
    "mysterious places on earth",
    "world records",
    "psychology and brain",
    "dinosaurs and prehistoric life",
    "quantum physics simple facts",
    "Indian history and culture",
    "solar system planets",
    "volcanoes and earthquakes",
    "sharks and ocean predators",
    "black holes and galaxies",
    "extreme weather phenomena",
    "ancient civilizations secrets",
]


class FactGenerator:

    def __init__(self):
        self.client      = Groq(api_key=Config.GROQ_API_KEY)
        self.used_titles = self._load_used_titles()
        self.used_topics = self._load_used_topics()

    def generate_fact_video(self, topic: str = None) -> dict | None:
        if not topic:
            topic = self._pick_fresh_topic()

        # Facts are Shorts — 1 or 2 facts only, 40-55 seconds total
        duration = random.randint(40, 55)
        facts_n  = random.randint(1, 2)

        prompt = self._build_prompt(topic, facts_n, duration)

        try:
            resp = self.client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.88,
                max_tokens=2500,
            )
            raw  = resp.choices[0].message.content
            data = self._extract_json(raw)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

        if not data:
            logger.error("Failed to parse fact JSON")
            return None

        data["content_type"]    = f"facts_{topic}"
        data["is_short"]        = True
        data["target_duration"] = duration
        data["mode"]            = "facts"
        data["characters"]      = [{"name": "NARRATOR", "voice_key": "narrator_female", "gender": "female"}]

        self.used_titles.append(data.get("title", ""))
        self.used_topics.append(topic)
        self._save_used_titles()
        self._save_used_topics()
        logger.info(f"Fact video ready: \"{data.get('title', '?')}\" | topic: {topic}")
        return data

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a viral Hindi YouTube facts creator. "
            "You write shocking, mind-blowing facts in simple Hindi that keep viewers hooked. "
            "ALWAYS respond with valid JSON only — no markdown, no code fences."
        )

    def _build_prompt(self, topic: str, facts_n: int, duration: int) -> str:
        avoid = ", ".join(self.used_titles[-20:]) if self.used_titles else "None"

        return f"""Create a viral Hindi YouTube facts Short video about: {topic}

FORMAT: YouTube Short (9:16 vertical, {duration} seconds)
FACTS COUNT: exactly {facts_n} fact(s) — no more
LANGUAGE: Hindi (Devanagari) — simple, clear, conversational
AVOID TITLES: {avoid}

RULES:
- Start with a SHOCKING hook line that grabs attention in 2-3 seconds
- Each fact must be mind-blowing and hard to believe — 2-3 Hindi sentences max
- Female voice will narrate (Swara AI voice)
- Cinematic visuals play in background — NO text in images at all
- End with "Aisa hi aur jaanne ke liye follow karo!"
- Each fact must be detailed — 4-6 Hindi sentences, explain WHY it's shocking
- estimated_duration must be 20-28 seconds per scene (enough time for voice narration)

Return ONLY this JSON:
{{
  "title": "Viral Hindi title — shocking, max 65 chars",
  "thumbnail_text": "Max 4 bold words",
  "thumbnail_mood": "dark|bright|mysterious|dramatic",
  "thumbnail_main_color": "#FF4444",
  "hook": "3-4 second shocking opening question in Hindi",
  "scenes": [
    {{
      "scene_number": 1,
      "fact_text": "Detailed Hindi narration — 4-6 sentences, explain the fact with wow details, shocking and clear",
      "image_prompts": [
        "Image 1 — wide establishing shot matching this fact, ultra-realistic, 8K, NO text, NO words, photorealistic, cinematic",
        "Image 2 — close-up dramatic detail of the same fact, different angle, ultra-realistic, 8K, NO text, NO words, photorealistic",
        "Image 3 — another stunning perspective of same fact, ultra-realistic, 8K, NO text, NO words, photorealistic, cinematic lighting"
      ],
      "estimated_duration": 22,
      "sfx": "wind|waves|space|forest|ambient",
      "music_mood": "mysterious|epic_cinematic|dramatic_orchestral|suspense",
      "motion_type": "zoom_in|zoom_out|pan_left|pan_right|tilt_up",
      "color_grade": "dark_dramatic|blue_cold|teal_orange|night_glow|golden_hour"
    }}
  ],
  "outro": "Aisa hi aur jaanne ke liye follow karo!",
  "tags": ["facts hindi", "amazing facts", "rochak tathya", "hindi facts"]
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

    def _pick_fresh_topic(self) -> str:
        # Avoid last 10 used topics; if all used, reset
        recent = set(self.used_topics[-10:])
        fresh  = [t for t in FACT_TOPICS if t not in recent]
        if not fresh:
            fresh = FACT_TOPICS
        return random.choice(fresh)

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

    def _load_used_topics(self) -> list:
        try:
            with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_used_topics(self):
        os.makedirs("output", exist_ok=True)
        with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.used_topics[-100:], f, ensure_ascii=False)
