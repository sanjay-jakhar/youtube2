import logging
import json
import re
from groq import Groq
from config import Config

logger = logging.getLogger(__name__)

BASE_TAGS = [
    "hindi kahani", "hindi story", "emotional story hindi",
    "ai story hindi", "animated story", "kahani", "bedtime story hindi",
    "moral story hindi", "short story hindi", "hindi animation",
]


class SEOGenerator:

    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)

    def generate(self, story: dict) -> dict:
        title    = story.get("title", "")
        genre    = story.get("genre", "emotional")
        is_short = story.get("is_short", False)
        tags     = list(story.get("tags", []))

        # Merge with base tags (deduplicate)
        all_tags = list(dict.fromkeys(tags + BASE_TAGS))[:500]  # YT allows 500 chars total

        prompt = self._build_prompt(title, genre, is_short)

        try:
            resp = self.client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a YouTube SEO expert for Hindi storytelling channels. Respond with valid JSON only."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.7,
                max_tokens=800,
            )
            raw  = resp.choices[0].message.content
            data = self._extract_json(raw)
        except Exception as e:
            logger.error(f"SEO generation failed: {e}")
            data = {}

        yt_title = data.get("title", title)
        description = data.get("description", self._fallback_description(title, genre))
        hashtags = data.get("hashtags", ["#HindiKahani", "#Story", "#HindiStory"])

        # Combine description with hashtags
        full_description = description + "\n\n" + " ".join(hashtags[:15])
        full_description += "\n\n" + self._standard_footer()

        return {
            "title":       yt_title[:100],          # YouTube limit
            "description": full_description[:5000],  # YouTube limit
            "tags":        all_tags,
            "category_id": "24",                     # Entertainment
            "language":    "hi",
            "is_short":    is_short,
        }

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_prompt(self, title: str, genre: str, is_short: bool) -> str:
        video_type = "YouTube Short (Shorts)" if is_short else "regular YouTube video"
        return f"""Create YouTube SEO for a Hindi {genre} story {video_type}.
Story title: "{title}"

Return JSON:
{{
  "title": "Viral Hindi YouTube title with emotion — max 90 chars, include genre keyword",
  "description": "3-4 paragraph Hindi+English description. Start with a hook. Include what the story is about. End with CTA (Subscribe karo!). 300-400 words.",
  "hashtags": ["#HindiKahani", "#HorrorStory", "#EmotionalStory", "#HindiStory", "#KahaniSuno", "#AIStory", "#AnimatedStory", ...10 more relevant]
}}"""

    @staticmethod
    def _fallback_description(title: str, genre: str) -> str:
        return (
            f"{title}\n\n"
            f"Aaj ki {genre} kahani aapko hila ke rakh degi! "
            f"Is kahani mein aapko milega emotion, suspense, aur ek aisa twist "
            f"jo aap kabhi nahi bhoolenge.\n\n"
            f"Hamara channel subscribe karo aur bell icon dabaao "
            f"taaki koi bhi nai kahani miss na ho!\n\n"
            f"Roz nayi kahaniyaan - sirf hamare channel par!"
        )

    @staticmethod
    def _standard_footer() -> str:
        return (
            "------------------------------\n"
            f"Channel: {Config.CHANNEL_NAME}\n"
            "Subscribe karein nayi kahaniyaon ke liye!\n"
            "Bell icon press karein!\n"
            "------------------------------\n"
            "#HindiKahani #Story #AIAnimation #HindiStories #KahaniSuno"
        )

    @staticmethod
    def _extract_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {}
