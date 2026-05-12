import os
import glob as _glob
from dotenv import load_dotenv

load_dotenv()

# Auto-detect and add FFmpeg to PATH (WinGet install location)
def _add_ffmpeg_to_path():
    pattern = os.path.expanduser(
        r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin"
    )
    matches = _glob.glob(pattern)
    if matches:
        bin_dir = matches[0]
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

_add_ffmpeg_to_path()

class Config:
    # ── API Keys ───────────────────────────────────────────────────────────────
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL   = "llama-3.3-70b-versatile"

    # ── YouTube ────────────────────────────────────────────────────────────────
    YT_CLIENT_SECRETS = "client_secrets.json"
    YT_TOKEN_FILE     = "youtube_token.json"
    CHANNEL_NAME      = os.getenv("CHANNEL_NAME", "AI Hindi Kahaniya")
    CHANNEL_LANGUAGE  = os.getenv("CHANNEL_LANGUAGE", "hi")

    # ── Story Settings ─────────────────────────────────────────────────────────
    PRIMARY_LANGUAGE  = os.getenv("PRIMARY_LANGUAGE", "hindi")
    STORIES_PER_DAY   = int(os.getenv("STORIES_PER_DAY", "2"))
    MIN_DURATION        = int(os.getenv("MIN_DURATION", "40"))   # seconds
    MAX_DURATION        = int(os.getenv("MAX_DURATION", "180"))  # seconds
    SHORTS_THRESHOLD    = 60    # < 60s → Shorts (vertical)
    SHORTS_MIN_DURATION = 45    # min seconds for a Short
    SHORTS_MAX_DURATION = 58    # max seconds for a Short

    # ── Video Resolutions ──────────────────────────────────────────────────────
    SHORTS_RES  = (1080, 1920)   # 9:16 vertical
    REGULAR_RES = (1920, 1080)   # 16:9 horizontal
    FPS         = 24

    # ── Upload Times (IST) ─────────────────────────────────────────────────────
    UPLOAD_TIME_1 = os.getenv("UPLOAD_TIME_1", "07:00")
    UPLOAD_TIME_2 = os.getenv("UPLOAD_TIME_2", "19:30")

    # ── Paths ──────────────────────────────────────────────────────────────────
    OUTPUT_DIR     = "output"
    STORIES_DIR    = f"{OUTPUT_DIR}/stories"
    AUDIO_DIR      = f"{OUTPUT_DIR}/audio"
    IMAGES_DIR     = f"{OUTPUT_DIR}/images"
    VIDEOS_DIR     = f"{OUTPUT_DIR}/videos"
    THUMBS_DIR     = f"{OUTPUT_DIR}/thumbnails"
    ASSETS_DIR     = "assets"
    MUSIC_DIR      = f"{ASSETS_DIR}/music"
    FONTS_DIR      = f"{ASSETS_DIR}/fonts"
    SFX_DIR        = f"{ASSETS_DIR}/sfx"
    LOGS_DIR       = "logs"

    # ── Image Generation (Pollinations.ai – free, no key) ─────────────────────
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt"
    IMAGE_WIDTH      = 1920
    IMAGE_HEIGHT     = 1080

    # ── Story Genres (kept for --story mode) ──────────────────────────────────
    GENRES = [
        "horror",       "mystery",    "emotional",   "motivational",
        "adventure",    "sci-fi",     "fantasy",     "love",
        "survival",     "thriller",   "funny",       "village",
        "kids",         "superhero",  "ghost",       "crime"
    ]

    # ── Cinematic Content Types (default mode) ─────────────────────────────────
    CONTENT_TYPES = [
        "extreme storm and hurricane",
        "massive flood disaster",
        "volcanic eruption",
        "wildfire spreading through forest",
        "underwater deep ocean exploration",
        "space exploration and galaxy",
        "future city 2075",
        "earthquake and city collapse",
        "arctic frozen world survival",
        "dangerous road journey through mountains",
        "animals escaping wildfire",
        "tsunami hitting coastline",
        "abandoned city reclaimed by nature",
        "meteor shower over earth",
        "desert survival extreme heat",
        "train journey through dangerous storm",
        "deep jungle wildlife encounter",
        "city submerged underwater",
        "blizzard whiteout survival",
        "car accident rescue mission",
        "lightning storm at night",
        "bridge collapse dramatic scene",
        "avalanche in mountains",
        "tornado destroying a town",
        "night sky aurora borealis timelapse",
        "rapid facts about universe",
        "earth from space stunning views",
        "ocean waves extreme storm",
        "drone footage over disaster zone",
        "fire rescue in burning building",
    ]

    # ── Hindi TTS Voices (edge-tts) — Swara female as default narrator ────────
    VOICES = {
        "narrator_male":   "hi-IN-SwaraNeural",   # switched to female (Swara)
        "narrator_female": "hi-IN-SwaraNeural",
        "male_young":      "ur-IN-SalmanNeural",   # Urdu male — natural for Hindi
        "female_young":    "hi-IN-SwaraNeural",
        "male_old":        "ur-IN-SalmanNeural",
        "female_old":      "hi-IN-SwaraNeural",
        "en_male":         "en-US-GuyNeural",
        "en_female":       "en-US-JennyNeural",
    }

    # ── Emotion → TTS params ───────────────────────────────────────────────────
    EMOTION_PARAMS = {
        "scared":      {"rate": "+10%", "pitch": "+8Hz"},
        "excited":     {"rate": "+35%", "pitch": "+5Hz"},
        "sad":         {"rate": "+5%",  "pitch": "-5Hz"},
        "angry":       {"rate": "+30%", "pitch": "+10Hz"},
        "whispering":  {"rate": "+5%",  "volume": "-20%"},
        "crying":      {"rate": "+5%",  "pitch": "-8Hz"},
        "mysterious":  {"rate": "+15%", "pitch": "-3Hz"},
        "happy":       {"rate": "+30%", "pitch": "+3Hz"},
        "normal":      {"rate": "+20%", "pitch": "+0Hz"},
    }
