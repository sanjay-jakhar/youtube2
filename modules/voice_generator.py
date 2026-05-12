import asyncio
import os
import logging
import edge_tts
from config import Config

logger = logging.getLogger(__name__)


class VoiceGenerator:
    """Generates Hindi speech using Microsoft Edge TTS (free, no API key)."""

    def generate(
        self,
        text: str,
        voice_key: str = "narrator_male",
        emotion: str = "normal",
        output_path: str = None,
    ) -> str | None:
        """
        Synthesize `text` and save to `output_path`.
        Returns the path on success, None on failure.
        """
        if not text or not text.strip():
            return None

        voice = Config.VOICES.get(voice_key, Config.VOICES["narrator_male"])
        params = Config.EMOTION_PARAMS.get(emotion, Config.EMOTION_PARAMS["normal"])

        if output_path is None:
            safe = text[:20].replace(" ", "_").replace("/", "_")
            output_path = os.path.join(Config.AUDIO_DIR, f"{safe}_{emotion}.mp3")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            asyncio.run(self._synthesize(text, voice, params, output_path))
            logger.debug(f"Audio saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"TTS failed for «{text[:30]}»: {e}")
            return None

    # ── Private ────────────────────────────────────────────────────────────────

    @staticmethod
    async def _synthesize(text: str, voice: str, params: dict, output_path: str):
        rate   = params.get("rate", "+0%")
        pitch  = params.get("pitch", "+0Hz")
        volume = params.get("volume", "+0%")

        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        await communicate.save(output_path)

    def generate_scene_audio(
        self,
        scene: dict,
        characters: list,
        scene_idx: int,
        story_id: str,
    ) -> tuple[str | None, list[dict]]:
        """
        Generate all audio for a scene (narration + dialogues) and merge them.
        Returns (merged_audio_path, subtitle_list).

        subtitle_list entries: {start, end, text, speaker}
        """
        char_map = {c["name"]: c for c in characters}
        segments = []    # (audio_path, duration)
        subtitles = []
        cursor = 0.0

        base_dir = os.path.join(Config.AUDIO_DIR, story_id)
        os.makedirs(base_dir, exist_ok=True)

        # 1. Narration
        narration = (scene.get("narration") or "").strip()
        if narration:
            path = os.path.join(base_dir, f"s{scene_idx:02d}_narration.mp3")
            result = self.generate(narration, "narrator_male", "normal", path)
            if result:
                dur = _audio_duration(result)
                subtitles.append({"start": cursor, "end": cursor + dur,
                                   "text": narration, "speaker": "NARRATOR"})
                segments.append((result, dur))
                cursor += dur

        # 2. Dialogues
        for d_idx, dlg in enumerate(scene.get("dialogues") or []):
            char_name = dlg.get("character", "NARRATOR")
            text      = (dlg.get("text") or "").strip()
            emotion   = dlg.get("emotion", "normal")

            if not text:
                continue

            char_info = char_map.get(char_name, {})
            voice_key = char_info.get("voice_key", "narrator_male")

            path = os.path.join(base_dir, f"s{scene_idx:02d}_d{d_idx:02d}.mp3")
            result = self.generate(text, voice_key, emotion, path)
            if result:
                dur = _audio_duration(result)
                display = f"{char_name}: {text}" if char_name != "NARRATOR" else text
                subtitles.append({"start": cursor, "end": cursor + dur,
                                   "text": display, "speaker": char_name})
                segments.append((result, dur))
                cursor += dur

        if not segments:
            return None, []

        # 3. Merge all segments sequentially
        merged_path = os.path.join(base_dir, f"s{scene_idx:02d}_merged.mp3")
        merged = _merge_audio_sequential([p for p, _ in segments], merged_path)

        total_dur = cursor
        return merged, subtitles, total_dur


def _audio_duration(path: str) -> float:
    """Return audio duration in seconds using ffprobe."""
    import subprocess, json as _json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", path],
            capture_output=True, text=True, timeout=30
        )
        info = _json.loads(result.stdout)
        return float(info["streams"][0]["duration"])
    except Exception:
        return 3.0   # fallback estimate


def _merge_audio_sequential(paths: list[str], output_path: str) -> str | None:
    """Concatenate audio files one after another using FFmpeg."""
    import subprocess, tempfile, os

    if len(paths) == 1:
        import shutil
        shutil.copy(paths[0], output_path)
        return output_path

    # Write concat list
    list_file = output_path + "_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in paths:
            abs_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_file, "-c", "copy", output_path],
            capture_output=True, check=True, timeout=120
        )
        os.remove(list_file)
        return output_path
    except Exception as e:
        logging.getLogger(__name__).error(f"Audio merge failed: {e}")
        if os.path.exists(list_file):
            os.remove(list_file)
        return None
