"""
Fact video generator — viral Hindi facts with shocking narration.
Female voice narrates mind-blowing facts over cinematic visuals.
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
    # Science & Space
    "universe and space shocking facts",
    "black holes and galaxies",
    "solar system planets",
    "quantum physics mind-blowing",
    "time travel science facts",
    "parallel universe theory",
    "sun and stars shocking facts",
    "moon mysteries and secrets",

    # Earth & Nature
    "deep ocean terrifying secrets",
    "earth's core and volcanoes",
    "extreme weather phenomena",
    "dinosaurs and prehistoric life",
    "dangerous animals shocking facts",
    "sharks and ocean predators",
    "mysterious places on earth",
    "ancient trees and forest secrets",

    # Human Body & Mind
    "human body amazing hidden facts",
    "brain and psychology shocking facts",
    "sleep and dreams science",
    "human senses unbelievable facts",
    "memory and consciousness facts",
    "fear and adrenaline science",

    # History & Civilization
    "ancient India history mysteries",
    "Indian history and culture shocking",
    "ancient civilizations secrets",
    "pyramids and egypt mysteries",
    "world wars hidden facts",
    "Indian kings and empires secrets",

    # Technology & Future
    "technology and AI shocking future",
    "internet hidden secrets",
    "robots and automation future",
    "space travel future facts",

    # Viral / Shocking
    "world records unbelievable facts",
    "money and wealth shocking facts",
    "food and eating shocking science",
    "animals with superpowers",
    "luck and coincidence shocking stories",
    "numbers and mathematics shocking",
    "optical illusions brain facts",
    "death and afterlife science",
]

# Opening hook templates to mix into prompts for variety
HOOK_STYLES = [
    "Kya aap jaante hain ki...",
    "99% log yeh nahi jaante...",
    "Yeh sun ke aapko yakeen nahi hoga...",
    "Vigyanik bhi hairaan hain ki...",
    "Agar aap yeh sach jaante toh...",
    "Aaj tak kisi ne aapko nahi bataya...",
    "Duniya ki sabse shocking sach...",
    "Yeh fact aapki zindagi badal dega...",
]


class FactGenerator:

    def __init__(self):
        self.client      = Groq(api_key=Config.GROQ_API_KEY)
        self.used_titles = self._load_used_titles()
        self.used_topics = self._load_used_topics()

    def generate_fact_video(self, topic: str = None) -> dict | None:
        if not topic:
            topic = self._pick_fresh_topic()

        duration = random.randint(45, 58)
        hook_style = random.choice(HOOK_STYLES)

        prompt = self._build_prompt(topic, duration, hook_style)

        try:
            resp = self.client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.92,
                max_tokens=2800,
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
            "Aap ek viral Hindi YouTube facts creator hain. "
            "Aap shocking, mind-blowing facts likhte hain jo viewers ko screen se chipka dete hain. "
            "Aapki style dramatic, emotional aur unbelievable hai. "
            "Har fact ek movie scene ki tarah feel hona chahiye. "
            "Sirf VALID JSON return karein — koi markdown nahi, koi code fences nahi."
        )

    def _build_prompt(self, topic: str, duration: int, hook_style: str) -> str:
        avoid = ", ".join(self.used_titles[-20:]) if self.used_titles else "None"

        return f"""Ek VIRAL Hindi YouTube Shorts fact video banao topic: {topic}

FORMAT: YouTube Short (9:16 vertical, {duration} seconds, 1 scene only)
LANGUAGE: Hindi (Devanagari) — simple, dramatic, emotional
HOOK STYLE: "{hook_style}" se shuru karo
AVOID TITLES: {avoid}

STRICT RULES:
1. Ek hi SCENE hoga jisme poori fact story hogi (40-55 seconds ki narration)
2. Narration 4 parts mein hona chahiye:
   - HOOK (2-3 lines): Shocking opening question ya statement — viewer ko rok do
   - FACT BODY (6-8 lines): Asli fact — numbers, details, comparisons, "kyon" aur "kaise" samjhao
   - WOW MOMENT (2-3 lines): Sabse shocking part — ekdum unbelievable reveal
   - CALL TO ACTION (1 line): "Aisa hi aur chahiye toh follow karo!"
3. SHOCKING facts likhni hain — real ya slightly exaggerated, viewer shocked hona chahiye
4. Numbers use karo: "93 crore kilometer", "10,000 saal pehle", "99.9% log nahi jaante"
5. Comparisons use karo: "Yeh Taj Mahal se 1000 guna bada hai"
6. 3 different image prompts dena — different angles of same topic, NO text in images
7. Image prompts must be in English — ultra-realistic, cinematic, photorealistic, 8K, NO text

Return ONLY this JSON (no markdown):
{{
  "title": "Viral shocking Hindi title — max 65 chars, use numbers if possible",
  "thumbnail_text": "3-4 shocking bold Hindi words",
  "thumbnail_mood": "dark|mysterious|bright|dramatic",
  "thumbnail_main_color": "#FF4444",
  "hook": "2-3 second shocking opening line in Hindi",
  "scenes": [
    {{
      "scene_number": 1,
      "fact_text": "Complete narration in Hindi — HOOK (3 lines) + FACT BODY (8 lines) + WOW MOMENT (3 lines) + CALL TO ACTION. Total 50-55 seconds when spoken. Use dramatic pauses with '...' Use shocking numbers and comparisons.",
      "image_prompts": [
        "Wide establishing shot matching {topic} — ultra-realistic photorealistic cinematic 8K dramatic lighting NO text NO words",
        "Close-up dramatic detail of same topic — different angle ultra-realistic 8K NO text stunning",
        "Another perspective of same topic — night sky or golden hour ultra-realistic cinematic NO text"
      ],
      "estimated_duration": 52,
      "sfx": "wind|space|waves|heartbeat|rumble",
      "music_mood": "mysterious|epic_cinematic|dramatic_orchestral|suspense",
      "motion_type": "zoom_in|zoom_out|pan_left|pan_right|tilt_up",
      "color_grade": "dark_dramatic|blue_cold|teal_orange|night_glow|golden_hour"
    }}
  ],
  "outro": "Aisa hi aur jaanne ke liye follow karo!",
  "genre": "{topic.split()[0]}",
  "tags": ["facts hindi", "amazing facts", "rochak tathya", "hindi facts", "{topic}"]
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
        recent = set(self.used_topics[-12:])
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
