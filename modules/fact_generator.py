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
            "Aap ek viral Hindi YouTube Shorts creator hain. "
            "Aap EK shocking, mind-blowing fact ke baare mein deep-dive karte hain — "
            "sirf ek fact, lekin itna detailed aur dramatic ki viewer hairan reh jaaye. "
            "Title mein KABHI bhi '5 facts', '10 facts', ya koi number mat likhna — "
            "sirf ek specific fact ka dramatic naam hona chahiye Hindi mein. "
            "Sirf VALID JSON return karein — koi markdown nahi, koi code fences nahi."
        )

    def _build_prompt(self, topic: str, duration: int, hook_style: str) -> str:
        avoid = ", ".join(self.used_titles[-20:]) if self.used_titles else "None"

        return f"""Ek VIRAL Hindi YouTube Short banao — SIRF EK shocking fact ke baare mein: {topic}

FORMAT: YouTube Short (9:16 vertical, {duration} seconds)
LANGUAGE: Sirf Hindi (Devanagari) — simple, dramatic, emotional
HOOK: "{hook_style}" style se shuru karo
AVOID TITLES: {avoid}

STRICT RULES:
1. SIRF EK hi specific fact — koi list nahi, koi "X facts" nahi
2. Title Hindi mein hona chahiye — dramatic, emotional, shocking
   GALAT: "5 Amazing Space Facts" / "10 Shocking Facts"
   SAHI: "सूरज का यह सच सुनकर आप कांप जाएंगे" / "इंसानी दिमाग का यह राज़ कोई नहीं जानता"
3. Narration ek hi continuous story ki tarah hona chahiye:
   - HOOK (3 lines): "{hook_style}" se shocking opening
   - DEEP DIVE (8-10 lines): Asli fact — numbers, comparisons, "kyon" aur "kaise"
   - WOW REVEAL (2-3 lines): Sabse unbelievable part
   - CTA (1 line): "Aisa hi aur jaanne ke liye follow karo!"
4. Numbers aur comparisons zaroor use karo
5. thumbnail_image_prompt = ek English sentence jo is fact ka best cinematic visual describe kare

Return ONLY this JSON (no markdown, no code fences):
{{
  "title": "Dramatic Hindi title about ONE specific fact — max 65 chars, NO numbers in title",
  "thumbnail_text": "3-4 bold Hindi words (Devanagari only)",
  "thumbnail_mood": "dark|mysterious|dramatic|scary|emotional",
  "thumbnail_image_prompt": "One cinematic English image prompt for this fact — ultra-realistic 8K photorealistic dramatic lighting NO text NO words",
  "hook": "2-3 second shocking Hindi opening line",
  "scenes": [
    {{
      "scene_number": 1,
      "fact_text": "Complete Hindi narration — HOOK + DEEP DIVE + WOW REVEAL + CTA. Total 50-55 seconds when spoken at normal pace. Use '...' for dramatic pauses. Use shocking numbers.",
      "image_prompts": [
        "Wide cinematic shot — ultra-realistic photorealistic 8K dramatic lighting NO text NO words",
        "Close-up dramatic detail — different angle ultra-realistic 8K stunning cinematic NO text",
        "Another dramatic angle — golden hour or night sky ultra-realistic cinematic NO text"
      ],
      "estimated_duration": 52,
      "sfx": "wind|space|waves|heartbeat|rumble|forest",
      "music_mood": "mysterious|epic_cinematic|dramatic_orchestral|suspense",
      "motion_type": "zoom_in|zoom_out|pan_left|pan_right|tilt_up",
      "color_grade": "dark_dramatic|blue_cold|teal_orange|night_glow|golden_hour"
    }}
  ],
  "outro": "Aisa hi aur jaanne ke liye follow karo!",
  "genre": "{topic.split()[0]}",
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
