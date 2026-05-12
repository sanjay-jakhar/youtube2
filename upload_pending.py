"""
Upload all pre-generated fact videos that haven't been uploaded yet.
Usage: python upload_pending.py [--privacy public|unlisted|private]
"""

import os
import sys
import json
import glob
import logging
import argparse
from datetime import datetime

import colorlog
from config import Config
from modules.seo_generator import SEOGenerator
from modules.youtube_uploader import YouTubeUploader

UPLOADED_LOG = "output/uploaded_ids.json"


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def load_uploaded_ids():
    try:
        with open(UPLOADED_LOG, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_uploaded_ids(ids: set):
    os.makedirs("output", exist_ok=True)
    with open(UPLOADED_LOG, "w") as f:
        json.dump(list(ids), f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--mode",    default="facts", help="Only upload videos with this mode (facts/cinematic/story/all)")
    parser.add_argument("--date",    default=None,    help="Only upload videos from this date prefix e.g. 20260512")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("upload_pending")

    seo_gen  = SEOGenerator()
    uploader = YouTubeUploader()

    uploaded_ids = load_uploaded_ids()

    stories_dir = Config.STORIES_DIR
    videos_dir  = Config.VIDEOS_DIR
    thumbs_dir  = Config.THUMBS_DIR

    json_files = sorted(glob.glob(os.path.join(stories_dir, "*.json")))
    logger.info(f"Found {len(json_files)} story files")

    results = []
    for json_path in json_files:
        video_id = os.path.splitext(os.path.basename(json_path))[0]

        # Date filter
        if args.date and not video_id.startswith(args.date):
            continue

        # Already uploaded
        if video_id in uploaded_ids:
            logger.info(f"Already uploaded: {video_id} — skipping")
            continue

        video_path = os.path.join(videos_dir, f"{video_id}.mp4")
        if not os.path.exists(video_path):
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Mode filter
        if args.mode != "all" and data.get("mode") != args.mode:
            continue

        title = data.get("title", video_id)
        safe_title = title.encode("ascii", "replace").decode("ascii")
        logger.info(f"Uploading: {safe_title}")

        thumb_path = os.path.join(thumbs_dir, f"{video_id}_thumb.jpg")
        thumbnail  = thumb_path if os.path.exists(thumb_path) else None

        seo   = seo_gen.generate(data)
        yt_id = uploader.upload(video_path, thumbnail, seo, data, privacy=args.privacy)

        if yt_id:
            logger.info(f"[LIVE] https://youtu.be/{yt_id}")
            uploaded_ids.add(video_id)
            save_uploaded_ids(uploaded_ids)
            results.append({"title": safe_title, "url": f"https://youtu.be/{yt_id}"})
        else:
            logger.error(f"Upload failed: {safe_title}")
            results.append({"title": safe_title, "url": None})

    print("\n" + "=" * 50)
    print(f"  Uploaded {sum(1 for r in results if r['url'])} / {len(results)} videos")
    print("=" * 50)
    for r in results:
        status = r["url"] or "FAILED"
        print(f"  {r['title'][:40]:<40}  {status}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
