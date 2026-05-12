"""Upload remaining 8 sample videos with delay between each to avoid API limits."""
import os, sys, time, logging

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/remaining_upload_log.txt", encoding="utf-8"),
    ],
)

from modules.pipeline import VideoPipeline

TOPICS = [
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
    print("  Uploading 8 Remaining Sample Videos")
    print("="*60 + "\n")

    for i, topic in enumerate(TOPICS, 1):
        print(f"\n[{i}/8] Starting: {topic}")
        print("-"*50)

        result = pipeline.run(genre=topic, upload=True, privacy="public", force_short=True)
        title  = result.get("title", "?")
        yt_id  = result.get("video_id") or result.get("yt_video_id")

        if result["status"] == "success" and yt_id:
            link = f"https://youtu.be/{yt_id}"
            print(f"[OK] {topic}")
            print(f"     Link: {link}")
            results.append({"topic": topic, "link": link})
        else:
            print(f"[FAIL] {topic} -- {result.get('error','unknown')}")
            results.append({"topic": topic, "link": "FAILED"})

        # Small delay between uploads to avoid rate limits
        if i < len(TOPICS):
            print("  Waiting 5s before next...")
            time.sleep(5)

    print("\n" + "="*60)
    print("  FINAL LINKS")
    print("="*60)
    for r in results:
        print(f"  {r['topic'][:38]:<38} {r['link']}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
