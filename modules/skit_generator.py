"""
Comedy skit generator — viral Indian AI character skits.
Style: Photorealistic AI images + Hindi narrator voiceover.
Format: manoranjan_tales / badmashgoku377 style — absurd characters in Indian settings.
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
USED_TOPICS_FILE = "output/used_topics.json"

# Viral scenario pool — absurd characters + Indian everyday situations
SKIT_SCENARIOS = [
    # Animals doing human things
    "Gorilla Mumbai ki sabzi mandi mein tamatar ka bhaav maang raha hai",
    "Mota orange cat auto-rickshaw driver se meter band karwane ki koshish kar raha hai",
    "Chimpanzee Indian school mein teacher ban gaya, bachche hairan hain",
    "Panda Indian dhaba mein unlimited thali kha raha hai, malik pareshan hai",
    "Lion Indian bank mein home loan maangne gaya, manager ka chehra dekho",
    "Bear Indian shaadi mein baraat mein naach raha hai, sab bhag rahe hain",
    "Monkey Mumbai local train mein window seat ke liye uncle se lad raha hai",
    "Gorilla IPL match mein VIP box mein baitha hai, popcorn kha raha hai",
    "Elephant ghodon ki jagah dulha leke aa gaya shaadi mein",
    "Dog IPS officer ban ke traffic chalaan kata raha hai",
    "Shark Indian swimming pool mein lifeguard se permission maang raha hai",
    "Penguin Rajasthan ki garmi mein ice cream bech raha hai",

    # Superheroes in Indian daily life
    "Red Hulk Indian village mein aaya, saree-wali reporter ka mic utha liya",
    "Spiderman Mumbai local train ki chhat pe chadh gaya, TC pakadne aaya",
    "Thor Indian dhobi ghat pe apna hammer dho raha hai",
    "Iron Man Delhi traffic jam mein phans gaya, petrol khatam",
    "Batman Indian chai tapri pe adrak wali chai pi raha hai raat ko",
    "Thanos Indian jugaad mechanic se infinity gauntlet repair karwa raha hai",
    "Captain America Indian uncle se bijli bill pe debate kar raha hai",
    "Superman Ola auto wale se kiraya kam karwa raha hai",
    "Spiderman UPSC exam hall mein naqal karte pakda gaya",
    "Hulk Indian hospital mein 'take a number' token le ke wait kar raha hai",
    "Spiderman Indian marriage bureau mein rishta dhundhne aaya",
    "Batman Indian ration shop mein aadhar card maang raha hai",

    # Babies doing adult things
    "6 mahine ka baby hospital mein doctor ko apni problem explain kar raha hai",
    "Baby corporate office mein CEO ki kursi pe baith ke meeting le raha hai",
    "Baby Supreme Court mein apna case khud lad raha hai",
    "Baby Ola driver ban ke cab chalaa raha hai, passenger hairan",
    "Baby UPSC interview de raha hai IAS banne ke liye",
    "Baby Indian parliament mein speech de raha hai",

    # Food characters with faces
    "Gussa pani puri apne aap ko khaane se rok raha hai street pe",
    "Angry samosa chai se dosti ka agreement sign kar raha hai",
    "Vada pav Mumbai mein Bollywood star ban gaya, paparazzi ke saath",
    "Jalebi police se bhaag rahi hai kyunki wo itni meethi hai ki sab pakadna chahte hain",
    "Bada sa idli Chennai mein auto mein chadh raha hai",

    # Fantasy creatures in India
    "Dinosaur Indian auto-rickshaw mein fit hone ki koshish kar raha hai",
    "Dragon Indian kitchen mein tandoori roti sek raha hai",
    "Mermaid Mumbai Juhu beach pe bhutta bech rahi hai",
    "Unicorn Indian shaadi mein ghoda ban gaya, sab pehchaan gaye",
    "Giant octopus Indian dhobi ghat pe kapde dho raha hai",
    "T-Rex Indian cricket match mein fielding kar raha hai",
]

HOOK_STYLES = [
    "Yeh dekh ke pet dard hoga hansne se...",
    "Yeh scene sirf India mein hi ho sakta hai...",
    "Jab yeh hua toh sab ne phone nikaal liya...",
    "Aaj tak aisa nahi dekha hoga...",
    "India mein kuch bhi ho sakta hai, yeh dekho...",
    "Yeh toh hona hi tha Indian style mein...",
    "Imagine karo agar yeh real mein ho jaata...",
    "Yeh video share karna mat bhoolo...",
]


class SkitGenerator:

    def __init__(self):
        self.client      = Groq(api_key=Config.GROQ_API_KEY)
        self.used_titles = self._load_json(USED_TITLES_FILE)
        self.used_topics = self._load_json(USED_TOPICS_FILE)

    def generate_skit(self, scenario: str = None) -> dict | None:
        if not scenario:
            scenario = self._pick_fresh_scenario()

        hook_style = random.choice(HOOK_STYLES)
        prompt     = self._build_prompt(scenario, hook_style)

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
            raw  = resp.choices[0].message.content
            data = self._extract_json(raw)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

        if not data or not data.get("scenes"):
            logger.error("Failed to parse skit JSON")
            return None

        data["content_type"] = "skit"
        data["is_short"]     = True
        data["mode"]         = "skit"
        data["scenario"]     = scenario
        data["characters"]   = [{"name": "NARRATOR", "voice_key": "narrator_female", "gender": "female"}]

        self.used_titles.append(data.get("title", ""))
        self.used_topics.append(scenario)
        self._save_json(USED_TITLES_FILE, self.used_titles[-500:])
        self._save_json(USED_TOPICS_FILE, self.used_topics[-100:])

        logger.info(f"Skit ready: \"{data.get('title','?')}\" | scenario: {scenario}")
        return data

    @staticmethod
    def _system_prompt() -> str:
        return (
            "Aap India ke sabse viral Hindi comedy shorts writer hain. "
            "Aapki specialty hai absurd Indian situations — animals, superheroes, babies "
            "India ki rozana zindagi mein. Har skit mein ek clear punchline hoti hai "
            "jo log apne friends ko bhejte hain. "
            "Narration fast, funny aur energetic hoti hai — jaise koi dost exciting "
            "story suna raha ho. Sirf VALID JSON return karo."
        )

    def _build_prompt(self, scenario: str, hook_style: str) -> str:
        avoid = ", ".join(self.used_titles[-15:]) if self.used_titles else "None"
        return f"""Ek VIRAL Hindi comedy skit banao is scenario pe:
"{scenario}"

HOOK STYLE: "{hook_style}"
AVOID TITLES: {avoid}

3 SCENES MEIN STORY (total ~50 seconds):

SCENE 1 (10-12 sec) — DRAMATIC ENTRY:
Character ka unexpected arrival. Logon ka shocked reaction. Setup establish karo.

SCENE 2 (25-28 sec) — MAIN COMEDY:
Character Indian situation se deal karta hai. Actual funny dialogue — character kya kehta hai,
doosra banda kya kehta hai. Indian jugaad, bhaav maangna, queue mein khada rehna — jo bhi situation ho.
Narrator dono characters ki awaaz mein bolta hai with clear name tags.

SCENE 3 (12-14 sec) — PUNCHLINE + CTA:
Sabse funny twist. Unexpected ending. "Yeh video apne uss dost ko bhejo jo yeh nahi jaanta... aur follow karo!"

RULES:
- Pure Hindi (Devanagari) narration — fast, funny, energetic
- Character dialogues with name: "Gorilla: 'Bhaiya...'" / "Sabzi wala: 'Sahab...'"
- Image prompts: ultra-realistic photorealistic 8K, Indian setting, NO text/words in image
- Each image must clearly show the character + Indian background
- Title: Funny Hindi — max 55 chars, no numbers

Return ONLY valid JSON:
{{
  "title": "Funny viral Hindi title — max 55 chars",
  "thumbnail_text": "3-4 bold Hindi words (Devanagari)",
  "thumbnail_mood": "funny|shocked|dramatic",
  "thumbnail_image_prompt": "Best funny scene — ultra-realistic 8K photorealistic, Indian setting, character clearly visible, NO text NO words",
  "hook": "First funny line of narration",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Hindi narration — narrator + character dialogues. Fast and funny. Use '...' for dramatic pauses.",
      "image_prompt": "ultra-realistic photorealistic 8K cinematic [character] in [Indian setting], [specific action], hyperdetailed, dramatic lighting, NO text NO words",
      "motion_prompt": "character walks confidently into frame, people around react with shock and amazement, natural fluid movement, cinematic",
      "emotion": "excited",
      "estimated_duration": 12
    }},
    {{
      "scene_number": 2,
      "narration": "Main comedy scene narration with dialogues.",
      "image_prompt": "ultra-realistic photorealistic 8K [character] [action] in [Indian setting], shocked people around, cinematic, NO text",
      "motion_prompt": "character gestures expressively while arguing or talking, other person reacts with surprise, both move naturally, funny interaction",
      "emotion": "happy",
      "estimated_duration": 26
    }},
    {{
      "scene_number": 3,
      "narration": "Punchline + CTA — 'Yeh video apne dost ko bhejo... aur follow karo aisi aur masti ke liye!'",
      "image_prompt": "ultra-realistic photorealistic 8K [character] funny final pose in [Indian setting], crowd reaction, cinematic, NO text",
      "motion_prompt": "character does a funny triumphant pose or walks away with swagger, crowd cheers or laughs, natural movement",
      "emotion": "excited",
      "estimated_duration": 13
    }}
  ],
  "tags": ["hindi comedy", "funny shorts", "indian funny video", "ai comedy hindi", "viral hindi"]
}}"""

    def _pick_fresh_scenario(self) -> str:
        recent = set(t.lower() for t in self.used_topics[-20:])
        fresh  = [s for s in SKIT_SCENARIOS if s.lower() not in recent]
        if not fresh:
            fresh = SKIT_SCENARIOS
        picked = random.choice(fresh)
        logger.info(f"Skit scenario: {picked}")
        return picked

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

    def _load_json(self, path: str) -> list:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_json(self, path: str, data: list):
        os.makedirs("output", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
