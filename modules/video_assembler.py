"""
Video assembler — builds the final MP4 from scene images, audio, and subtitles.

Pipeline per scene:
  image → Ken Burns clip (FFmpeg zoompan)
  audio → scene voice track
  subtitle overlay → burned-in via FFmpeg drawtext

Final steps:
  concat all scenes → mix background music → export HD MP4
"""

import os
import json
import random
import logging
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

from config import Config

logger = logging.getLogger(__name__)


class VideoAssembler:

    def assemble(
        self,
        story: dict,
        scene_assets: list[dict],
        story_id: str,
    ) -> str | None:
        """
        scene_assets: list of dicts:
          {
            image_path: str,
            audio_path: str | None,
            subtitles: [{start, end, text, speaker}],
            duration: float,
          }
        Returns path to final MP4, or None on failure.
        """
        is_short = story.get("is_short", False)
        resolution = Config.SHORTS_RES if is_short else Config.REGULAR_RES
        W, H = resolution

        out_dir = os.path.join(Config.VIDEOS_DIR, story_id)
        os.makedirs(out_dir, exist_ok=True)

        # ── 1. Build one video clip per scene ──────────────────────────────────
        scene_clips = []
        global_subtitles = []
        time_cursor = 0.0

        for idx, asset in enumerate(scene_assets):
            clip_path = self._build_scene_clip(idx, asset, W, H, out_dir)
            if clip_path:
                scene_clips.append(clip_path)
                for sub in asset.get("subtitles", []):
                    global_subtitles.append({
                        "start":   time_cursor + sub["start"],
                        "end":     time_cursor + sub["end"],
                        "text":    sub["text"],
                        "speaker": sub.get("speaker", ""),
                    })
            time_cursor += asset.get("duration", 5.0)

        if not scene_clips:
            logger.error("No scene clips generated — aborting assembly")
            return None

        # ── 2. Concatenate scenes ──────────────────────────────────────────────
        concat_path = os.path.join(out_dir, "concat_raw.mp4")
        if not self._concat_clips(scene_clips, concat_path):
            return None

        # ── 3. Add background music ────────────────────────────────────────────
        music_path = self._pick_music()
        with_music = os.path.join(out_dir, "with_music.mp4")
        if music_path:
            self._mix_music(concat_path, music_path, with_music)
        else:
            with_music = concat_path

        # ── 4. Normalize audio levels ─────────────────────────────────────────
        normalized = os.path.join(out_dir, "normalized.mp4")
        pre_sub = self._normalize_audio(with_music, normalized) or with_music

        # ── 5. Burn subtitles (only if there are any) ────────────────────────
        final_path = os.path.join(Config.VIDEOS_DIR, f"{story_id}.mp4")

        if global_subtitles:
            srt_path = os.path.join(out_dir, "subs.srt")
            _write_srt(global_subtitles, srt_path)
            font_path = self._get_font()
            self._burn_subtitles(pre_sub, srt_path, final_path, font_path, W, H)
        else:
            # No subtitles (cinematic mode) — just copy/rename
            import shutil
            shutil.copy(pre_sub, final_path)

        logger.info(f"Final video: {final_path}")
        return final_path

    # ── Scene clip builder ─────────────────────────────────────────────────────

    def _build_scene_clip(
        self, idx: int, asset: dict, W: int, H: int, out_dir: str
    ) -> str | None:
        image_path   = asset.get("image_path")
        audio_path   = asset.get("audio_path")
        sfx_type     = asset.get("sfx", "")
        motion_type  = asset.get("motion_type", "random")
        color_grade  = asset.get("color_grade", "")
        duration     = max(asset.get("duration", 5.0), 3.0)

        sfx_raw = os.path.join(out_dir, f"sfx_{idx:02d}.aac")

        if not audio_path or not os.path.exists(str(audio_path)):
            # Cinematic mode: no voice — use SFX as primary audio
            sfx_to_use = sfx_type if (sfx_type and sfx_type != "silence") else "wind"
            audio_path = self._generate_sfx(sfx_to_use, duration, sfx_raw)
        else:
            # Story mode: mix SFX under voice audio
            if sfx_type and sfx_type != "silence":
                sfx_path = self._generate_sfx(sfx_type, duration, sfx_raw)
                if sfx_path:
                    mixed = os.path.join(out_dir, f"audio_sfx_{idx:02d}.aac")
                    result = self._mix_sfx_into_audio(audio_path, sfx_path, mixed)
                    if result:
                        audio_path = mixed

        # Support multiple images per scene — cycle through them
        image_paths = asset.get("image_paths") or ([image_path] if image_path else [])
        image_paths = [p for p in image_paths if p and os.path.exists(p)]
        if not image_paths:
            logger.warning(f"Scene {idx}: missing image, skipping")
            return None

        out_clip  = os.path.join(out_dir, f"scene_{idx:02d}.mp4")
        raw_video = os.path.join(out_dir, f"scene_{idx:02d}_raw.mp4")

        if len(image_paths) > 1:
            # Multiple images: split duration, create sub-clips, concatenate
            sub_dur    = duration / len(image_paths)
            sub_clips  = []
            motions    = ["zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up"]
            for i, img in enumerate(image_paths):
                sub_raw = os.path.join(out_dir, f"scene_{idx:02d}_img{i}_raw.mp4")
                _generate_ken_burns(img, sub_raw, W, H, sub_dur, Config.FPS, motions[i % len(motions)])
                if os.path.exists(sub_raw):
                    sub_clips.append(sub_raw)
            if sub_clips:
                _concat_video_only(sub_clips, raw_video)
        else:
            # Single image — normal Ken Burns
            _generate_ken_burns(image_paths[0], raw_video, W, H, duration, Config.FPS, motion_type)

        # Apply color grading if specified
        if color_grade and os.path.exists(raw_video):
            graded = os.path.join(out_dir, f"scene_{idx:02d}_graded.mp4")
            if _apply_color_grade(raw_video, graded, color_grade):
                raw_video = graded

        if not os.path.exists(raw_video):
            # Fallback: static image clip
            raw_video = _static_image_clip(image_path, out_dir, idx, W, H, duration)
            if not raw_video:
                return None

        # Mux with audio
        if audio_path and os.path.exists(audio_path):
            audio_fwd = audio_path.replace("\\", "/")
            raw_fwd   = raw_video.replace("\\", "/")
            out_fwd   = out_clip.replace("\\", "/")
            cmd = [
                "ffmpeg", "-y",
                "-i", raw_fwd,
                "-i", audio_fwd,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-shortest", out_fwd,
            ]
        else:
            raw_fwd = raw_video.replace("\\", "/")
            out_fwd = out_clip.replace("\\", "/")
            cmd = [
                "ffmpeg", "-y",
                "-i", raw_fwd,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac",
                "-t", str(duration), out_fwd,
            ]

        result = _run_ffmpeg(cmd, out_clip)
        # Clean up raw video
        if os.path.exists(raw_video):
            try:
                os.remove(raw_video)
            except Exception:
                pass
        return result

    # ── Concatenation ──────────────────────────────────────────────────────────

    @staticmethod
    def _concat_clips(clips: list[str], output: str) -> bool:
        list_file = output + "_list.txt"
        with open(list_file, "w") as f:
            for c in clips:
                abs_p = os.path.abspath(c).replace("\\", "/")
                f.write(f"file '{abs_p}'\n")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            output,
        ]
        ok = _run_ffmpeg(cmd, output) is not None
        if os.path.exists(list_file):
            os.remove(list_file)
        return ok

    # ── Music mixing ───────────────────────────────────────────────────────────

    @staticmethod
    def _mix_music(video: str, music: str, output: str):
        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-stream_loop", "-1", "-i", music,
            "-filter_complex",
            "[0:a]volume=1.0[va];[1:a]volume=0.35[ma];[va][ma]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output,
        ]
        result = _run_ffmpeg(cmd, output)
        if not result:
            import shutil
            shutil.copy(video, output)

    # ── Audio normalization ────────────────────────────────────────────────────

    @staticmethod
    def _normalize_audio(video: str, output: str) -> str | None:
        """Normalize audio levels — uses simple dynaudnorm (works on any audio level)."""
        vid_fwd = video.replace("\\", "/")
        out_fwd = output.replace("\\", "/")
        cmd = [
            "ffmpeg", "-y", "-i", vid_fwd,
            "-af", "dynaudnorm=f=150:g=15",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            out_fwd,
        ]
        return _run_ffmpeg(cmd, output)

    # ── SFX generation ─────────────────────────────────────────────────────────

    @staticmethod
    def _generate_sfx(sfx_type: str, duration: float, out_path: str) -> str | None:
        """Generate ambient SFX audio using FFmpeg built-in synthesizers."""
        SFX_FILTERS = {
            "wind":       "aevalsrc=sin(2*PI*500*t)*0.04+sin(2*PI*300*t)*0.02:s=44100:c=stereo",
            "rain":       "aevalsrc=(random(0)-0.5)*0.06:s=44100:c=stereo",
            "heartbeat":  "aevalsrc=sin(2*PI*1.2*t)*abs(sin(2*PI*1.2*t))*0.25:s=44100:c=stereo",
            "fire":       "aevalsrc=(random(0)-0.5)*0.05+sin(2*PI*80*t)*0.02:s=44100:c=stereo",
            "crowd":      "aevalsrc=(random(0)-0.5)*0.04+sin(2*PI*350*t)*0.01:s=44100:c=stereo",
            "thunder":    "aevalsrc=sin(2*PI*60*t)*0.4:s=44100:c=stereo",
            "waves":      "aevalsrc=sin(2*PI*200*t)*0.05+sin(2*PI*150*t)*0.04+(random(0)-0.5)*0.03:s=44100:c=stereo",
            "storm":      "aevalsrc=sin(2*PI*400*t)*0.03+(random(0)-0.5)*0.07+sin(2*PI*60*t)*0.2:s=44100:c=stereo",
            "forest":     "aevalsrc=sin(2*PI*600*t)*0.02+sin(2*PI*800*t)*0.01+(random(0)-0.5)*0.02:s=44100:c=stereo",
            "rumble":     "aevalsrc=sin(2*PI*45*t)*0.3+sin(2*PI*30*t)*0.2:s=44100:c=stereo",
            "explosion":  "aevalsrc=(random(0)-0.5)*0.4+sin(2*PI*50*t)*0.3:s=44100:c=stereo",
            "waterfall":  "aevalsrc=(random(0)-0.5)*0.07+sin(2*PI*300*t)*0.03:s=44100:c=stereo",
            "earthquake": "aevalsrc=sin(2*PI*25*t)*0.4+(random(0)-0.5)*0.1:s=44100:c=stereo",
            "ocean":      "aevalsrc=sin(2*PI*180*t)*0.05+sin(2*PI*120*t)*0.04+(random(0)-0.5)*0.03:s=44100:c=stereo",
            # fallback ambient
            "ambient":    "aevalsrc=sin(2*PI*400*t)*0.02+(random(0)-0.5)*0.02:s=44100:c=stereo",
        }
        key = sfx_type.lower().strip() if sfx_type else ""
        sfx_filter = SFX_FILTERS.get(key) or SFX_FILTERS.get("ambient")
        out_fwd = out_path.replace("\\", "/")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", sfx_filter,
            "-t", str(duration), "-c:a", "aac", "-b:a", "96k",
            out_fwd,
        ]
        return _run_ffmpeg(cmd, out_path)

    @staticmethod
    def _mix_sfx_into_audio(voice_path: str, sfx_path: str, output: str) -> str | None:
        """Mix SFX at 8% volume under voice audio."""
        cmd = [
            "ffmpeg", "-y",
            "-i", voice_path.replace("\\", "/"),
            "-i", sfx_path.replace("\\", "/"),
            "-filter_complex",
            "[0:a]volume=1.0[v];[1:a]volume=0.08[s];[v][s]amix=inputs=2:duration=first[out]",
            "-map", "[out]", "-c:a", "aac", "-b:a", "128k",
            output.replace("\\", "/"),
        ]
        return _run_ffmpeg(cmd, output)

    # ── Subtitles ──────────────────────────────────────────────────────────────

    @staticmethod
    def _burn_subtitles(video: str, srt: str, output: str, font: str | None, W: int, H: int):
        # Small captions at bottom — outline style, no opaque box
        font_size = max(18, H // 55)

        srt_abs = os.path.abspath(srt).replace("\\", "/").replace(":", "\\:")

        if font:
            style = (f"FontSize={font_size},PrimaryColour=&H00FFFFFF,"
                     f"BorderStyle=1,Outline=2,Shadow=0,MarginV=60,Alignment=2")
            sub_filter = f"subtitles='{srt_abs}':fontsdir={os.path.dirname(font).replace(chr(92),'/')}:force_style='{style}'"
        else:
            style = (f"FontSize={font_size},PrimaryColour=&H00FFFFFF,"
                     f"BorderStyle=1,Outline=2,Shadow=0,MarginV=60,Alignment=2")
            sub_filter = f"subtitles='{srt_abs}':force_style='{style}'"

        vid_fwd = video.replace("\\", "/")
        out_fwd = output.replace("\\", "/")
        cmd = [
            "ffmpeg", "-y", "-i", vid_fwd,
            "-vf", sub_filter,
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            out_fwd,
        ]
        result = _run_ffmpeg(cmd, output)
        if not result:
            import shutil
            shutil.copy(video, output)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _pick_music() -> str | None:
        music_dir = Config.MUSIC_DIR
        if not os.path.isdir(music_dir):
            return None
        files = [
            os.path.join(music_dir, f)
            for f in os.listdir(music_dir)
            if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a"))
        ]
        return random.choice(files) if files else None

    @staticmethod
    def _get_font() -> str | None:
        candidates = [
            os.path.join(Config.FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
            os.path.join(Config.FONTS_DIR, "NotoSans-Regular.ttf"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None


# ── Utility functions ──────────────────────────────────────────────────────────

COLOR_GRADE_FILTERS = {
    "dark_dramatic":   "eq=contrast=1.15:saturation=1.2:brightness=-0.05:gamma=0.92",
    "golden_hour":     "colorchannelmixer=rr=1.15:rg=0.05:rb=-0.1:gg=1.0:bb=0.75,eq=saturation=1.4",
    "blue_cold":       "colorchannelmixer=bb=1.3:rb=0.05:gb=0.05,eq=saturation=0.85:contrast=1.1",
    "teal_orange":     "colorchannelmixer=rr=1.1:rb=-0.05:bb=0.85:gb=0.05,eq=saturation=1.3",
    "night_glow":      "eq=brightness=-0.08:saturation=0.9:contrast=0.9,colorchannelmixer=bb=1.25:rb=0.05",
    "warm_fire":       "colorchannelmixer=rr=1.25:rg=0.05:rb=-0.15:gg=0.9:bb=0.6,eq=saturation=1.5",
    "deep_ocean":      "colorchannelmixer=gb=0.08:bb=1.3,eq=saturation=1.2:contrast=1.1",
    "dusty_vintage":   "eq=saturation=0.8:contrast=0.92:brightness=0.03,colorchannelmixer=rr=1.08:bb=0.85",
}


def _concat_video_only(clips: list, output: str) -> bool:
    """Concatenate video-only clips (no audio) into one file."""
    list_file = output + "_list.txt"
    with open(list_file, "w") as f:
        for c in clips:
            abs_p = os.path.abspath(c).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-an", output,
    ]
    ok = _run_ffmpeg(cmd, output) is not None
    if os.path.exists(list_file):
        try:
            os.remove(list_file)
        except Exception:
            pass
    # Clean up sub-clips
    for c in clips:
        try:
            os.remove(c)
        except Exception:
            pass
    return ok


def _apply_color_grade(video: str, output: str, grade: str) -> str | None:
    """Apply cinematic color grading to a video clip."""
    vf = COLOR_GRADE_FILTERS.get(grade)
    if not vf:
        return None
    cmd = [
        "ffmpeg", "-y", "-i", video.replace("\\", "/"),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-an", output.replace("\\", "/"),
    ]
    return _run_ffmpeg(cmd, output)


def _run_ffmpeg(cmd: list, output: str) -> str | None:
    import sys
    kwargs = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
    try:
        result = subprocess.run(
            cmd, capture_output=True, check=True, timeout=600, **kwargs
        )
        if os.path.exists(output):
            return output
        logger.error(f"FFmpeg produced no output file: {output}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")
        # Find actual error line (skip build info)
        error_lines = [l for l in stderr.split("\n") if "Error" in l or "error" in l or "Invalid" in l]
        logger.error(f"FFmpeg failed: {'; '.join(error_lines[-5:]) if error_lines else stderr[-300:]}")
    except Exception as e:
        logger.error(f"FFmpeg exception: {e}")
    return None


def _generate_ken_burns(image_path: str, output: str, W: int, H: int,
                        duration: float, fps: int = 24, motion_type: str = "random"):
    """
    Create a Ken Burns (zoom + pan) video with fade-in/fade-out transitions.
    Pipes raw RGB frames to FFmpeg. No ImageMagick or zoompan filter needed.
    """
    from PIL import Image
    import numpy as np

    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        logger.error(f"Cannot open image for Ken Burns: {e}")
        return

    n_frames = int(duration * fps)
    src_w = int(W * 1.3)
    src_h = int(H * 1.3)

    img_ratio    = img.width / img.height
    target_ratio = src_w / src_h
    if img_ratio > target_ratio:
        new_h = src_h
        new_w = int(src_h * img_ratio)
    else:
        new_w = src_w
        new_h = int(src_w / img_ratio)

    img     = img.resize((new_w, new_h), Image.LANCZOS)
    img_arr = np.array(img, dtype=np.float32)

    # Motion type determines camera movement
    MOTION_MAP = {
        "zoom_in":   (0.5, 0.5, 0.0, 0.0),
        "zoom_out":  (0.0, 0.0, 0.5, 0.5),
        "pan_left":  (1.0, 0.5, 0.0, 0.5),
        "pan_right": (0.0, 0.5, 1.0, 0.5),
        "tilt_up":   (0.5, 1.0, 0.5, 0.0),
        "tilt_down": (0.5, 0.0, 0.5, 1.0),
        "parallax":  (0.0, 0.0, 1.0, 1.0),
        "handheld":  (0.3, 0.3, 0.7, 0.7),
    }
    if motion_type in MOTION_MAP:
        sx, sy, ex, ey = MOTION_MAP[motion_type]
    else:
        sx, sy, ex, ey = random.choice(list(MOTION_MAP.values()))

    FADE_FRAMES = min(int(fps * 0.4), n_frames // 5)  # 0.4s fade, max 20% of clip

    output_fwd = output.replace("\\", "/")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-an", output_fwd,
    ]

    try:
        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        max_x = new_w - W
        max_y = new_h - H

        for i in range(n_frames):
            t = i / max(n_frames - 1, 1)
            x = int(max_x * (sx + (ex - sx) * t))
            y = int(max_y * (sy + (ey - sy) * t))
            x = max(0, min(x, max_x))
            y = max(0, min(y, max_y))

            frame = img_arr[y:y + H, x:x + W].copy()
            if frame.shape[0] != H or frame.shape[1] != W:
                from PIL import Image as _PIL
                frame = np.array(_PIL.fromarray(frame.astype(np.uint8)).resize((W, H), _PIL.LANCZOS), dtype=np.float32)

            # Smooth fade-in / fade-out
            if FADE_FRAMES > 0:
                if i < FADE_FRAMES:
                    frame *= i / FADE_FRAMES
                elif i >= n_frames - FADE_FRAMES:
                    frame *= (n_frames - i) / FADE_FRAMES

            proc.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())

        proc.stdin.close()
        proc.wait(timeout=300)
        logger.info(f"Ken Burns video created: {output}")
    except Exception as e:
        logger.error(f"Ken Burns generation error: {e}")
        try:
            proc.kill()
        except Exception:
            pass


def _static_image_clip(image_path: str, out_dir: str, idx: int,
                        W: int, H: int, duration: float) -> str | None:
    """Fallback: create a simple static-image video clip."""
    out = os.path.join(out_dir, f"scene_{idx:02d}_static.mp4")
    img_fwd = image_path.replace("\\", "/")
    out_fwd = out.replace("\\", "/")
    vf = (f"scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", img_fwd,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", vf,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-t", str(duration), "-r", "24",
        out_fwd,
    ]
    return _run_ffmpeg(cmd, out)


def _generate_silent_audio(duration: float, out_dir: str, idx: int) -> str:
    path = os.path.join(out_dir, f"silent_{idx}.mp3")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:a", "mp3",
        path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
    return path


def _write_srt(subtitles: list[dict], path: str):
    def fmt(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(path, "w", encoding="utf-8") as f:
        for i, sub in enumerate(subtitles, 1):
            text = sub["text"]
            # Truncate long subtitles to ~60 chars per line
            if len(text) > 60:
                text = text[:57] + "..."
            f.write(f"{i}\n")
            f.write(f"{fmt(sub['start'])} --> {fmt(sub['end'])}\n")
            f.write(f"{text}\n\n")
