"""
AI YouTube Storytelling Automation
====================================
Usage:
  python main.py                  # Make 1 video now and upload
  python main.py --genre horror   # Force a specific genre
  python main.py --no-upload      # Make video but don't upload
  python main.py --schedule       # Start 24/7 automated scheduler
  python main.py --count 2        # Make N videos back to back
  python main.py --test           # Quick pipeline test (no upload)
"""

import argparse
import logging
import os
import sys
import random

import colorlog

from config import Config


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s — %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "red,bg_white",
        }
    ))

    file_handler = logging.FileHandler(
        os.path.join(Config.LOGS_DIR, "automation.log"),
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    ))

    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(file_handler)


def check_requirements():
    """Warn about missing API keys / files before running."""
    ok = True
    if not Config.GROQ_API_KEY:
        print("[X]  GROQ_API_KEY is not set in .env")
        ok = False
    else:
        print("[OK] Groq API key found")

    if not os.path.exists(Config.YT_CLIENT_SECRETS):
        print("[!]  client_secrets.json not found -- YouTube upload will be skipped")
        print("     Run setup_youtube.py to enable uploading")
    else:
        print("[OK] YouTube client_secrets.json found")

    import shutil
    if shutil.which("ffmpeg") is None:
        print("[X]  FFmpeg not found in PATH -- required for video assembly")
        ok = False
    else:
        print("[OK] FFmpeg found")

    return ok


def main():
    parser = argparse.ArgumentParser(description="AI Hindi YouTube Storytelling Bot")
    parser.add_argument("--genre",      help="Content type or story genre")
    parser.add_argument("--no-upload",  action="store_true", help="Skip YouTube upload")
    parser.add_argument("--schedule",   action="store_true", help="Run 24/7 scheduler")
    parser.add_argument("--count",      type=int, default=1, help="Number of videos to make")
    parser.add_argument("--test",       action="store_true", help="Test run — no upload")
    parser.add_argument("--shorts",     action="store_true", default=True, help="Force YouTube Shorts (under 60s, 9:16 vertical) — default ON")
    parser.add_argument("--story",      action="store_true", help="Story mode — Hindi narration (legacy)")
    parser.add_argument("--facts",      action="store_true", help="Facts mode — female voice narrates Hindi facts over cinematic visuals")
    parser.add_argument("--cinematic",  action="store_true", help="Cinematic mode — pure visuals, no narration")
    parser.add_argument("--privacy",    default="public", choices=["public", "unlisted", "private"])
    args = parser.parse_args()

    # Default to facts mode when no mode flag is given
    if not args.story and not args.facts and not args.cinematic:
        args.facts = True

    setup_logging()
    logger = logging.getLogger("main")

    print("\n" + "=" * 60)
    print("  AI Hindi YouTube Storytelling System")
    print("=" * 60 + "\n")

    if not check_requirements():
        sys.exit(1)

    if args.schedule:
        logger.info("Starting 24/7 scheduler…")
        from modules.scheduler import DailyScheduler
        DailyScheduler().start()
        return

    from modules.pipeline import VideoPipeline
    pipeline = VideoPipeline()

    upload = not args.no_upload and not args.test
    count  = args.count if not args.test else 1

    any_failed = False

    for i in range(count):
        if args.genre:
            genre = args.genre
        elif args.facts:
            genre = None  # FactGenerator will pick a fresh topic automatically
        else:
            genre = random.choice(Config.GENRES)
        logger.info(f"Video {i+1}/{count} — genre: {genre}")

        result = pipeline.run(
            genre=genre,
            upload=upload,
            privacy=args.privacy,
            force_short=args.shorts,
            story_mode=args.story,
            facts_mode=args.facts,
            cinematic_mode=args.cinematic,
        )

        def safe(s):
            return str(s).encode("ascii", "replace").decode("ascii") if s else ""

        if result["status"] == "success":
            yt_id = result.get("video_id")
            if upload and not yt_id:
                print(f"\n[FAIL] Video {i+1} generated but YouTube upload FAILED!")
                print(f"    Title: {safe(result.get('title'))}")
                print(f"    File:  {safe(result.get('video_path'))}")
                print("    Check: YouTube channel exists? Token valid? API quota ok?")
                any_failed = True
            else:
                print(f"\n[OK] Video {i+1} done!")
                print(f"    Title:  {safe(result.get('title'))}")
                if yt_id:
                    print(f"    URL:    https://youtu.be/{yt_id}")
                if result.get("video_path"):
                    print(f"    File:   {result['video_path']}")
        else:
            print(f"\n[FAIL] Video {i+1} failed: {safe(result.get('error'))}")
            any_failed = True

    if any_failed:
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Done! Check the output/ folder for your videos.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
