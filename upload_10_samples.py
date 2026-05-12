"""Upload 9 sample videos sequentially (storm already running separately)."""
import os
import sys
import logging
import random

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/sample_upload_log.txt", encoding="utf-8"),
    ],
)

from config import Config
from modules.pipeline import VideoPipeline

TOPICS = [
    "volcanic eruption",
    "underwater deep ocean exploration",
    "space exploration and galaxy",
    "wildfire spreading through forest",
    "future city 2075",
    "animals escaping wildfire",
    "tsunami hitting coastline",
    "car accident rescue mission",
    "arctic frozen world survival",
]

def main():
    pipeline = VideoPipeline()
    results  = []

    print("\n" + "="*60)
    print("  Uploading 9 Sample Videos to YouTube")
    print("="*60 + "\n")

    for i, topic in enumerate(TOPICS, 1):
        print(f"\n[{i}/9] Starting: {topic}")
        print("-" * 50)

        result = pipeline.run(
            genre=topic,
            upload=True,
            privacy="public",
            force_short=True,
        )

        title = result.get("title", "?")
        yt_id = result.get("video_id") or result.get("yt_video_id")

        if result["status"] == "success" and yt_id:
            link = f"https://youtu.be/{yt_id}"
            print(f"[OK] {topic}")
            print(f"     Title: {title.encode('ascii','replace').decode()}")
            print(f"     Link:  {link}")
            results.append({"topic": topic, "title": str(title), "link": link})
        else:
            print(f"[FAIL] {topic} -- {result.get('error','unknown error')}")
            results.append({"topic": topic, "title": str(title), "link": "FAILED"})

    print("\n" + "="*60)
    print("  ALL DONE — Final Links")
    print("="*60)
    for r in results:
        print(f"  {r['topic'][:35]:<35} {r['link']}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
