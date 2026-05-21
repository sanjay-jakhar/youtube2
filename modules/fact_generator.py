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
from modules.trending_fetcher import fetch_trending_topics

logger = logging.getLogger(__name__)

USED_TITLES_FILE  = "output/used_titles.json"
USED_TOPICS_FILE  = "output/used_topics.json"

FACT_TOPICS = [
    # Mystery & Dark Secrets (highest views in India)
    "Bharat ke sabse bade raaz jo sarkar chhupaati hai",
    "Taj Mahal ke andar ka sach jo koi nahi jaanta",
    "duniya ki sabse mysterious jagah jo science explain nahi kar sakti",
    "insaan ke marne ke baad kya hota hai — science ne kya khoja",
    "ancient Indian temples ke andar chhupi technology",
    "Bermuda Triangle ka asli sach — ek hi shocking reason",
    "duniya ke sabse khatarnak conspiracy jo sach nikli",
    "history ke sabse bade jhooth jo humein padhaye gaye",

    # Human Mind & Psychology (very viral)
    "hamare dimaag ki ek aisi power jo hum use nahi karte",
    "neend mein aisa kya hota hai jo aapko pata nahi",
    "insaan ka subconscious mind kitna powerful hai — ek shocking truth",
    "fear aur darr — ye actually aapko strong banata hai kaise",
    "kya insaan sach mein sixth sense use kar sakta hai",
    "akela rehna insaan ke dimaag ko kya karta hai",

    # India & Spiritual (huge audience)
    "Ramayana aur Mahabharata mein chupi ek science jo aaj prove hui",
    "Shiva ke damru ki frequency — science ne kya khoja",
    "Hindu temples south ki taraf kyon bane hote hain — shocking science",
    "kumbh mela ka aisa raaz jo vigyan bhi nahi samjha",
    "India mein ek aisi jagah jahan gravity kaam nahi karti",
    "Garuda Purana mein likha death ke baad ka sach",

    # Money & Success Psychology (huge engagement)
    "ameer log subah 5 baje kyon uthte hain — brain science",
    "paisa kamane ka ek psychological secret jo school nahi sikhata",
    "duniya ke sabse ameer insaan ne apni pehli kamayi kaise ki",
    "amir aur gareeb ki soch mein ek asli fark",

    # Space & Universe (always trending)
    "black hole ke andar jaane par aapko kya dikhega",
    "sun ke andar ek aisi cheez hai jo poori dharti se badi hai",
    "NASA ne ek aisi awaaz record ki jo space mein suni gayi",
    "duniya se 7 din baad ek asteroid kitni door se guzrega",
    "parallel universe actually exist karti hai — proof kya hai",

    # Health & Body Secrets (high retention)
    "hamare sharir mein ek aisa organ hai jiska kaam science abhi bhi nahi jaanti",
    "roz subah khaali pet ek glass paani pine se kya hota hai body ko",
    "insaani aansu mein chupi ek science jo aapko hairaan kar de",
    "pet mein 500 crore bacteria hain — ye aapki zindagi control karte hain",

    # Animals with Superpowers (always viral)
    "ek aisa jaanwar jo marne ke baad bhi apne dushman ko maar sakta hai",
    "mantis shrimp ki aankhon ki power — insaan iska 10% bhi nahi dekh sakta",
    "crows insaan jaisi planning karte hain — proof kya hai",
    "jellyfish immortal kyun hai — science ka shocking answer",

    # Dark History (very viral in India)
    "Chandragupta Maurya ne kaise poori duniya jeetne ka plan banaya tha",
    "1947 mein India ne kya kho diya jo shayad kabhi wapas nahi aayega",
    "Nazi Germany ka ek aisa experiment jo insaniyat ki sabse badi galti thi",
    "Cleopatra ke khazane ka sach — abhi bhi nahi mila",
]

# Viral hook styles — emotional, curious, fear-inducing
HOOK_STYLES = [
    "Yeh sunkr aapke roye khade ho jayenge...",
    "99% log apni puri zindagi yeh nahi jaante...",
    "Agar aapne yeh 60 second nahi dekhe toh aap bahut kuch miss kar rahe ho...",
    "Yeh raaz jaan ke aapki zindagi badal jayegi...",
    "Science ne prove kar diya — aur log abhi bhi andheron mein hain...",
    "Aaj tak kisi ne aapko yeh sach nahi bataya...",
    "Mujhe yeh share karte hue dar lag raha hai lekin sach batana zaroori hai...",
    "Yeh fact itna scary hai ki log believe nahi karte...",
    "Ek sach jo government nahi chahti ki aap jaano...",
    "Yeh dekh ke aap raat bhar so nahi paoge...",
]

# Topics to SKIP from trending news (dry, not engaging for shorts)
SKIP_TRENDING_KEYWORDS = [
    "election", "result", "vote", "percent turnout", "poll", "seat",
    "stock", "share price", "market", "nifty", "sensex", "rupee", "dollar",
    "rrb", "ssc", "exam", "admit card", "answer key",
    "match score", "ipl score", "cricket score",
    "weather", "rain", "temperature",
    "minister", "parliament", "bill passed", "lok sabha",
    "accident", "fire", "flood latest",
]


class FactGenerator:

    def __init__(self):
        self.client         = Groq(api_key=Config.GROQ_API_KEY)
        self.used_titles    = self._load_used_titles()
        self.used_topics    = self._load_used_topics()
        self._trending_ctx  = {}  # title -> description for prompt context

    def generate_fact_video(self, topic: str = None) -> dict | None:
        news_context = ""
        if not topic:
            topic, news_context = self._pick_fresh_topic()

        duration   = random.randint(45, 58)
        hook_style = random.choice(HOOK_STYLES)

        prompt = self._build_prompt(topic, duration, hook_style, news_context)

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
            "Aap India ke #1 viral Hindi YouTube Shorts writer hain. "
            "Aapki videos log scroll karna band kar dete hain — kyunki pehli line mein hi "
            "itna curiosity ya darr hota hai ki koi skip nahi kar sakta. "
            "Aap ek KAHANI ki tarah batate hain — seedha facts nahi, emotional journey. "
            "Har line mein suspense hona chahiye. Viewer ko lagna chahiye ki yeh sirf unke liye hai. "
            "Title mein koi number mat likho. Sirf VALID JSON return karo."
        )

    def _build_prompt(self, topic: str, duration: int, hook_style: str, news_context: str = "") -> str:
        avoid = ", ".join(self.used_titles[-20:]) if self.used_titles else "None"

        return f"""Topic: {topic}

Ek aisa Hindi YouTube Short likho jo log skip na kar paayein.

LANGUAGE: Pure Hindi (Devanagari script) — jaise ek dost baat kar raha ho
HOOK STYLE: "{hook_style}"
DURATION: {duration} seconds
AVOID TITLES: {avoid}

NARRATION STRUCTURE (yahi formula viral hota hai):
1. HOOK (5-6 sec): Itna shocking ya curiosity-inducing ki haath ruk jaaye — "{hook_style}" se shuru karo. Koi direct sawaal ya ek unbelievable claim.
2. TENSION BUILD (10-12 sec): Thoda aur andar le jaao — koi number, comparison, ya "aur yeh toh sirf shuruaat hai..."
3. MAIN REVELATION (25-28 sec): Asli shocking truth — easy language mein, real numbers, real examples. Jaise kisi dost ko bata rahe ho. Dramatic pauses ke liye '...' use karo.
4. EMOTIONAL PEAK (7-8 sec): Sabse unbelievable ya emotional part — yahan viewer ko goosebumps aane chahiye.
5. CTA (3-4 sec): "Yeh video apne uss dost ko bhejo jise yeh pata nahi... aur follow karo aisi aur sacchi baatein jaanne ke liye."

RULES:
- Sirf EK topic — koi list nahi, koi "X cheezein" nahi
- Title dramatic Hindi mein — max 60 characters — emotional ya curiosity hook wala
- Numbers real aur specific hone chahiye (e.g. "37 trillion cells", "4.6 billion saal")
- thumbnail_image_prompt: Ultra-cinematic English prompt — NO text, NO words in image

Return ONLY valid JSON:
{{
  "title": "Viral Hindi title — emotional/shocking/curiosity — max 60 chars, NO numbers",
  "thumbnail_text": "3-4 bold Hindi words jo thumbnail pe chalein (Devanagari)",
  "thumbnail_mood": "dark|mysterious|dramatic|scary|emotional|spiritual",
  "thumbnail_image_prompt": "Cinematic ultra-realistic 8K English prompt — dramatic lighting, no text, no words, photorealistic",
  "hook": "First shocking line of narration",
  "scenes": [
    {{
      "scene_number": 1,
      "fact_text": "Complete Hindi narration following the 5-part structure above. 50-55 seconds at normal pace. Use '...' for dramatic pauses. Pure Devanagari Hindi only.",
      "image_prompts": [
        "Opening wide cinematic shot — ultra-realistic 8K dramatic lighting, no text",
        "Close-up intense detail shot — different dramatic angle, ultra-realistic 8K, no text",
        "Final emotional/shocking reveal shot — cinematic masterpiece, ultra-realistic 8K, no text"
      ],
      "estimated_duration": 52,
      "sfx": "heartbeat|wind|thunder|waves|rumble|forest|fire",
      "music_mood": "suspense|mysterious|epic_cinematic|dramatic_orchestral|emotional",
      "motion_type": "zoom_in|zoom_out|pan_left|tilt_up|pan_right",
      "color_grade": "dark_dramatic|night_glow|blue_cold|teal_orange|golden_hour|warm_fire"
    }}
  ],
  "genre": "mystery|psychology|history|science|spiritual|motivation",
  "tags": ["hindi facts", "rochak tathya", "amazing facts hindi", "viral hindi", "shocking facts"]
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

    def _pick_fresh_topic(self) -> tuple[str, str]:
        """Returns (topic_string, news_context_string). Uses curated viral topics always."""
        recent = set(t.lower() for t in self.used_topics[-20:])

        # Always use our curated viral topic list — trending news topics are too dry
        fresh = [t for t in FACT_TOPICS if t.lower() not in recent]
        if not fresh:
            fresh = FACT_TOPICS
        picked = random.choice(fresh)
        logger.info(f"Topic selected: {picked}")
        return picked, ""

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
