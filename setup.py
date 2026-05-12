"""
One-time setup: downloads Hindi font, creates .env, verifies FFmpeg.
Run this FIRST before anything else.
"""

import os
import sys
import shutil
import subprocess
import urllib.request


FONT_URLS = {
    "NotoSansDevanagari-Regular.ttf": (
        "https://github.com/notofonts/devanagari/raw/main/fonts/NotoSansDevanagari/"
        "unhinted/ttf/NotoSansDevanagari-Regular.ttf"
    ),
    "NotoSansDevanagari-Bold.ttf": (
        "https://github.com/notofonts/devanagari/raw/main/fonts/NotoSansDevanagari/"
        "unhinted/ttf/NotoSansDevanagari-Bold.ttf"
    ),
}

DIRS = [
    "output/stories", "output/audio", "output/images",
    "output/videos",  "output/thumbnails",
    "assets/music", "assets/fonts", "assets/sfx", "logs",
]


def check_python():
    v = sys.version_info
    if v < (3, 10):
        print(f"❌ Python 3.10+ required. You have {v.major}.{v.minor}")
        sys.exit(1)
    print(f"✅ Python {v.major}.{v.minor}.{v.micro}")


def check_ffmpeg():
    if shutil.which("ffmpeg"):
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        ver = result.stdout.split("\n")[0]
        print(f"✅ {ver}")
        return True
    else:
        print("❌ FFmpeg NOT found in PATH")
        print("   Download: https://github.com/BtbN/FFmpeg-Builds/releases")
        print("   → ffmpeg-master-latest-win64-gpl.zip")
        print("   → Extract → add bin/ folder to System PATH")
        return False


def create_dirs():
    for d in DIRS:
        os.makedirs(d, exist_ok=True)
    print("✅ Output directories created")


def create_env():
    if os.path.exists(".env"):
        print("✅ .env already exists (skipping)")
        return
    shutil.copy(".env.example", ".env")
    print("✅ .env created from template")
    print("   → Open .env and paste your GROQ_API_KEY")


def download_fonts():
    fonts_dir = "assets/fonts"
    all_ok = True
    for filename, url in FONT_URLS.items():
        dest = os.path.join(fonts_dir, filename)
        if os.path.exists(dest):
            print(f"✅ Font already exists: {filename}")
            continue
        print(f"⬇️  Downloading {filename}…")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"✅ Font saved: {dest}")
        except Exception as e:
            print(f"⚠️  Font download failed ({e})")
            print(f"   Download manually from: {url}")
            print(f"   Save to: {dest}")
            all_ok = False
    return all_ok


def install_packages():
    print("\n📦 Installing Python packages…")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        capture_output=False
    )
    if result.returncode == 0:
        print("✅ All packages installed")
    else:
        print("❌ Package installation had errors — check above output")


def print_music_instructions():
    print("\n🎵 Background Music (optional but recommended)")
    print("   Add royalty-free MP3 files to: assets/music/")
    print("   Good free sources:")
    print("   • https://pixabay.com/music/ (search: suspense, emotional)")
    print("   • https://freemusicarchive.org")
    print("   • YouTube Audio Library (download from YouTube Studio)")
    print("   → Download 5–10 tracks for variety")


def main():
    print("\n" + "═"*60)
    print("  🎬  AI YouTube Storytelling — One-Time Setup")
    print("═"*60 + "\n")

    check_python()

    ffmpeg_ok = check_ffmpeg()
    create_dirs()
    create_env()

    print("\n⬇️  Downloading Hindi fonts…")
    download_fonts()

    install_packages()
    print_music_instructions()

    print("\n" + "═"*60)
    print("  Setup complete! Next steps:")
    print()
    print("  1. Open .env  →  paste your GROQ_API_KEY")
    if not ffmpeg_ok:
        print("  2. Install FFmpeg and add to PATH (see above)")
    print("  3. Download some music → assets/music/")
    print("  4. Run: python setup_youtube.py  (for uploading)")
    print("  5. Run: python main.py --test    (test without upload)")
    print("  6. Run: python main.py           (make + upload 1 video)")
    print("  7. Run: python main.py --schedule (start 24/7 mode)")
    print("═"*60 + "\n")


if __name__ == "__main__":
    main()
