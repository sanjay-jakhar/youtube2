"""
Main video production pipeline — orchestrates all modules for one video.
Supports two modes:
  - cinematic (default): AI concept + visuals + SFX only, no narration
  - story: Hindi story narration (legacy mode via --story flag)
"""

import os
import json
import logging
import uuid
import random
from datetime import datetime

from config import Config
from modules.concept_generator import ConceptGenerator
from modules.story_generator   import StoryGenerator
from modules.fact_generator    import FactGenerator
from modules.skit_generator    import SkitGenerator
from modules.video_generator   import VideoGenerator
from modules.voice_generator   import VoiceGenerator
from modules.image_generator   import ImageGenerator
from modules.video_assembler   import VideoAssembler
from modules.thumbnail_creator import ThumbnailCreator
from modules.seo_generator     import SEOGenerator
from modules.youtube_uploader  import YouTubeUploader

logger = logging.getLogger(__name__)


class VideoPipeline:

    def __init__(self):
        self.concept_gen = ConceptGenerator()
        self.story_gen   = StoryGenerator()
        self.fact_gen    = FactGenerator()
        self.skit_gen    = SkitGenerator()
        self.video_gen   = VideoGenerator()
        self.voice_gen   = VoiceGenerator()
        self.img_gen     = ImageGenerator()
        self.video_asm   = VideoAssembler()
        self.thumb_cr    = ThumbnailCreator()
        self.seo_gen     = SEOGenerator()
        self.uploader    = YouTubeUploader()

    def run(
        self,
        genre: str = None,
        upload: bool = True,
        privacy: str = "public",
        force_short: bool = False,
        story_mode: bool = False,
        facts_mode: bool = False,
        cinematic_mode: bool = False,
        skit_mode: bool = False,
    ) -> dict:
        mode = ("skit" if skit_mode else
                "facts" if facts_mode else
                "story" if story_mode else "cinematic")
        video_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:6]
        logger.info(f"Pipeline START | id={video_id} | mode={mode}")

        result = {"video_id_local": video_id, "status": "failed", "yt_video_id": None, "title": None}

        try:
            if skit_mode:
                result = self._run_skit_mode(video_id, genre, upload, privacy, result)
            elif facts_mode:
                result = self._run_facts_mode(video_id, genre, upload, privacy, result)
            elif story_mode:
                result = self._run_story_mode(video_id, genre, upload, privacy, force_short, result)
            else:
                result = self._run_cinematic_mode(video_id, genre, upload, privacy, force_short, result)
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            result["error"] = str(e)

        logger.info(f"Pipeline END | status={result['status']}")
        return result

    # ── Skit mode (viral Indian comedy) ──────────────────────────────────────

    def _run_skit_mode(self, video_id, scenario, upload, privacy, result):
        logger.info("Step 1/6 — Generating comedy skit...")
        data = self.skit_gen.generate_skit(scenario)
        if not data:
            raise RuntimeError("Skit generation failed")

        result["title"] = data.get("title")
        self._save_json(data, video_id)

        logger.info("Step 2/6 — Generating scene images + audio...")
        scene_assets = self._process_skit_scenes(data, video_id)
        if not scene_assets:
            raise RuntimeError("All skit scenes failed")

        logger.info("Step 3/6 — Assembling video...")
        video_path = self.video_asm.assemble(data, scene_assets, video_id)
        if not video_path:
            raise RuntimeError("Video assembly failed")

        logger.info("Step 4/6 — Generating thumbnail...")
        thumb_prompt = (data.get("thumbnail_image_prompt")
                        or data.get("scenes", [{}])[0].get("image_prompt", "funny Indian comedy scene"))
        thumb_base = self.img_gen.generate_thumbnail_image(
            thumb_prompt, video_id, mood=data.get("thumbnail_mood", "funny")
        )
        thumbnail = self.thumb_cr.create(data, video_id, thumb_base)

        logger.info("Step 5/6 — Generating SEO...")
        seo = self.seo_gen.generate(data)

        if upload:
            logger.info("Step 6/6 — Uploading to YouTube...")
            yt_id = self.uploader.upload(video_path, thumbnail, seo, data, privacy=privacy)
            result["yt_video_id"] = yt_id
            result["video_id"]    = yt_id
            if yt_id:
                logger.info(f"[LIVE] https://youtu.be/{yt_id}")
        else:
            logger.info(f"Step 6/6 — Skipped. File: {video_path}")
            result["video_id"] = None

        result["status"]     = "success"
        result["video_path"] = video_path
        return result

    def _process_skit_scenes(self, data: dict, video_id: str) -> list[dict]:
        scenes       = data.get("scenes", [])
        scene_assets = []

        for idx, scene in enumerate(scenes):
            logger.info(f"  Skit scene {idx+1}/{len(scenes)}...")

            # 1. Generate character image
            img_path = self.img_gen.generate_scene_image(
                prompt=scene.get("image_prompt", "funny Indian scene cinematic"),
                scene_idx=idx,
                story_id=video_id,
                is_short=True,
            )

            # 2. Animate image with Kling AI → moving character video
            video_path = None
            if img_path and os.path.exists(img_path):
                motion_prompt = scene.get("motion_prompt", "character moves naturally, cinematic fluid motion")
                vid_dir  = os.path.join("output/videos", video_id)
                os.makedirs(vid_dir, exist_ok=True)
                vid_file = os.path.join(vid_dir, f"s{idx:02d}_kling.mp4")
                logger.info(f"  Animating scene {idx+1} with Kling AI...")
                video_path = self.video_gen.animate(
                    image_path=img_path,
                    motion_prompt=motion_prompt,
                    output_path=vid_file,
                    duration=5,
                )
                if video_path:
                    logger.info(f"  Scene {idx+1} animated: {video_path}")
                else:
                    logger.warning(f"  Scene {idx+1} animation failed — using static image")

            # 3. Generate voice narration
            audio_path = None
            actual_dur = float(scene.get("estimated_duration", 15))
            narration  = scene.get("narration", "").strip()

            if narration:
                audio_dir  = os.path.join("output/audio", video_id)
                os.makedirs(audio_dir, exist_ok=True)
                audio_file = os.path.join(audio_dir, f"s{idx:02d}_skit.mp3")

                result = self.voice_gen.generate(
                    text=narration,
                    voice_key="narrator_female",
                    emotion=scene.get("emotion", "excited"),
                    output_path=audio_file,
                )
                if result:
                    from modules.voice_generator import _audio_duration
                    actual_dur = _audio_duration(result)
                    audio_path = result

            scene_assets.append({
                "video_path":  video_path,   # Kling animated video (takes priority)
                "image_path":  img_path,     # fallback if animation failed
                "image_paths": [img_path] if img_path else [],
                "audio_path":  audio_path,
                "subtitles":   [],
                "duration":    max(actual_dur, float(scene.get("estimated_duration", 15))),
                "sfx":         "crowd",
                "music_mood":  "funny",
                "motion_type": random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right"]),
                "color_grade": "teal_orange",
            })

        return scene_assets

    # ── Facts mode ────────────────────────────────────────────────────────────

    def _run_facts_mode(self, video_id, topic, upload, privacy, result):
        logger.info("Step 1/6 — Generating fact concept...")
        data = self.fact_gen.generate_fact_video(topic)
        if not data:
            raise RuntimeError("Fact generation failed")

        result["title"] = data.get("title")
        self._save_json(data, video_id)

        logger.info("Step 2/6 — Generating scene images + audio...")
        scene_assets = self._process_fact_scenes(data, video_id)
        if not scene_assets:
            raise RuntimeError("All fact scenes failed")

        logger.info("Step 3/6 — Assembling video...")
        video_path = self.video_asm.assemble(data, scene_assets, video_id)
        if not video_path:
            raise RuntimeError("Video assembly failed")

        logger.info("Step 4/6 — Generating thumbnail...")
        scene0       = data.get("scenes", [{}])[0]
        thumb_prompt = (data.get("thumbnail_image_prompt")
                        or scene0.get("thumbnail_image_prompt")
                        or (scene0.get("image_prompts") or [""])[0]
                        or scene0.get("image_prompt", "cinematic dramatic scene"))
        thumb_base   = self.img_gen.generate_thumbnail_image(thumb_prompt, video_id, mood=data.get("thumbnail_mood", "dramatic"))
        thumbnail    = self.thumb_cr.create(data, video_id, thumb_base)

        logger.info("Step 5/6 — Generating SEO...")
        seo = self.seo_gen.generate(data)

        if upload:
            logger.info("Step 6/6 — Uploading to YouTube...")
            yt_id = self.uploader.upload(video_path, thumbnail, seo, data, privacy=privacy)
            result["yt_video_id"] = yt_id
            result["video_id"]    = yt_id
            if yt_id:
                logger.info(f"[LIVE] https://youtu.be/{yt_id}")
        else:
            logger.info(f"Step 6/6 — Skipped. File: {video_path}")
            result["video_id"] = None

        result["status"]     = "success"
        result["video_path"] = video_path
        return result

    def _process_fact_scenes(self, data: dict, video_id: str) -> list[dict]:
        scenes      = data.get("scenes", [])
        characters  = data.get("characters", [])
        scene_assets = []

        for idx, scene in enumerate(scenes):
            logger.info(f"  Fact scene {idx+1}/{len(scenes)}...")

            # Support multiple image prompts per scene (2-3 images cycling)
            image_prompts = scene.get("image_prompts") or [scene.get("image_prompt", "amazing cinematic visual")]
            img_paths = []
            for i, prompt in enumerate(image_prompts):
                img_path = self.img_gen.generate_scene_image(
                    prompt=prompt,
                    scene_idx=idx * 10 + i,
                    story_id=video_id,
                    is_short=True,
                )
                if img_path:
                    img_paths.append(img_path)
            if not img_paths:
                img_paths = [None]

            # fact_text already contains full narration (hook + deep dive + outro)
            narration = scene.get("fact_text", "")

            # Generate female voice narration
            audio_path   = None
            subtitles    = []
            actual_dur   = float(scene.get("estimated_duration", 22))

            if narration.strip():
                import os as _os
                audio_dir = _os.path.join("output/audio", video_id)
                _os.makedirs(audio_dir, exist_ok=True)
                audio_file = _os.path.join(audio_dir, f"s{idx:02d}_fact.mp3")

                result = self.voice_gen.generate(
                    text=narration,
                    voice_key="narrator_female",
                    emotion="mysterious" if idx == 0 else "normal",
                    output_path=audio_file,
                )
                if result:
                    from modules.voice_generator import _audio_duration
                    actual_dur = _audio_duration(result)
                    audio_path = result
                    subtitles  = []  # No burned subtitles — clean screen

            scene_assets.append({
                "image_paths": img_paths,
                "image_path":  img_paths[0],  # backwards compat
                "audio_path":  audio_path,
                "subtitles":   subtitles,
                "duration":    max(actual_dur, float(scene.get("estimated_duration", 22))),
                "sfx":         scene.get("sfx", "ambient"),
                "music_mood":  scene.get("music_mood", "mysterious"),
                "motion_type": scene.get("motion_type", "zoom_in"),
                "color_grade": scene.get("color_grade", "dark_dramatic"),
            })

        return scene_assets

    # ── Cinematic mode (default) ───────────────────────────────────────────────

    def _run_cinematic_mode(self, story_id, genre, upload, privacy, force_short, result):
        logger.info("Step 1/6 — Generating cinematic concept...")
        concept = self.concept_gen.generate_concept(genre, force_short=force_short)
        if not concept:
            raise RuntimeError("Concept generation failed")

        result["title"] = concept.get("title")
        self._save_json(concept, story_id)

        logger.info("Step 2/6 — Generating scene images...")
        scene_assets = self._process_cinematic_scenes(concept, story_id)
        if not scene_assets:
            raise RuntimeError("All scenes failed to process")

        logger.info("Step 3/6 — Assembling video...")
        video_path = self.video_asm.assemble(concept, scene_assets, story_id)
        if not video_path:
            raise RuntimeError("Video assembly failed")

        logger.info("Step 4/6 — Generating thumbnail...")
        thumb_prompt = concept.get("scenes", [{}])[0].get("image_prompt", "dramatic cinematic scene")
        thumb_base   = self.img_gen.generate_thumbnail_image(thumb_prompt, story_id, mood=concept.get("thumbnail_mood", "dramatic"))
        thumbnail    = self.thumb_cr.create(concept, story_id, thumb_base)

        logger.info("Step 5/6 — Generating SEO...")
        seo = self.seo_gen.generate(concept)

        if upload:
            logger.info("Step 6/6 — Uploading to YouTube...")
            yt_id = self.uploader.upload(video_path, thumbnail, seo, concept, privacy=privacy)
            result["yt_video_id"] = yt_id
            if yt_id:
                logger.info(f"[LIVE] https://youtu.be/{yt_id}")
        else:
            logger.info(f"Step 6/6 — Skipped. File: {video_path}")

        result["status"]     = "success"
        result["video_path"] = video_path
        # Alias so callers using old key still work
        result["video_id"]   = result["yt_video_id"]
        return result

    def _process_cinematic_scenes(self, concept: dict, story_id: str) -> list[dict]:
        scenes      = concept.get("scenes", [])
        scene_assets = []

        for idx, scene in enumerate(scenes):
            logger.info(f"  Scene {idx+1}/{len(scenes)}...")

            img_path = self.img_gen.generate_scene_image(
                prompt=scene.get("image_prompt", "dramatic cinematic landscape"),
                scene_idx=idx,
                story_id=story_id,
                is_short=concept.get("is_short", False),
            )

            duration = float(scene.get("estimated_duration", 10))

            scene_assets.append({
                "image_path":  img_path,
                "audio_path":  None,       # no narration in cinematic mode
                "subtitles":   [],
                "duration":    duration,
                "sfx":         scene.get("sfx"),
                "music_mood":  scene.get("music_mood"),
                "motion_type": scene.get("motion_type", "random"),
                "color_grade": scene.get("color_grade", ""),
            })

        return scene_assets

    # ── Story mode (legacy --story flag) ──────────────────────────────────────

    def _run_story_mode(self, story_id, genre, upload, privacy, force_short, result):
        logger.info("Step 1/7 — Generating Hindi story...")
        story = self.story_gen.generate_story(genre, force_short=force_short)
        if not story:
            raise RuntimeError("Story generation failed")

        result["title"] = story.get("title")
        self._save_json(story, story_id)

        logger.info("Step 2/7 — Processing scenes (images + audio)...")
        scene_assets = self._process_story_scenes(story, story_id)
        if not scene_assets:
            raise RuntimeError("All scenes failed to process")

        logger.info("Step 3/7 — Assembling video...")
        video_path = self.video_asm.assemble(story, scene_assets, story_id)
        if not video_path:
            raise RuntimeError("Video assembly failed")

        logger.info("Step 4/7 — Generating thumbnail...")
        thumb_prompt = story.get("scenes", [{}])[0].get("image_prompt", "dramatic cinematic scene")
        thumb_base   = self.img_gen.generate_thumbnail_image(thumb_prompt, story_id, mood=story.get("thumbnail_mood", "dramatic"))
        thumbnail    = self.thumb_cr.create(story, story_id, thumb_base)

        logger.info("Step 5/7 — Generating SEO...")
        seo = self.seo_gen.generate(story)

        if upload:
            logger.info("Step 6/7 — Uploading to YouTube...")
            yt_id = self.uploader.upload(video_path, thumbnail, seo, story, privacy=privacy)
            result["yt_video_id"] = yt_id
            if yt_id:
                logger.info(f"[LIVE] https://youtu.be/{yt_id}")
        else:
            logger.info(f"Step 6/7 — Skipped. File: {video_path}")

        logger.info("Step 7/7 — Done!")
        result["status"]     = "success"
        result["video_path"] = video_path
        result["video_id"]   = result.get("yt_video_id")
        return result

    def _process_story_scenes(self, story: dict, story_id: str) -> list[dict]:
        characters   = story.get("characters", [])
        scene_assets = []

        for idx, scene in enumerate(story.get("scenes", [])):
            logger.info(f"  Scene {idx+1}/{len(story['scenes'])}...")

            img_path = self.img_gen.generate_scene_image(
                prompt=scene.get("image_prompt", "cinematic dramatic scene"),
                scene_idx=idx,
                story_id=story_id,
                is_short=story.get("is_short", False),
            )

            audio_path, subtitles, actual_duration = self.voice_gen.generate_scene_audio(
                scene=scene,
                characters=characters,
                scene_idx=idx,
                story_id=story_id,
            )

            if actual_duration <= 0:
                actual_duration = float(scene.get("estimated_duration", 10))

            scene_assets.append({
                "image_path":  img_path,
                "audio_path":  audio_path,
                "subtitles":   subtitles,
                "duration":    actual_duration,
                "sfx":         scene.get("sfx"),
                "music_mood":  scene.get("music_mood"),
                "motion_type": "random",
                "color_grade": "",
            })

        return scene_assets

    @staticmethod
    def _save_json(data: dict, video_id: str):
        os.makedirs(Config.STORIES_DIR, exist_ok=True)
        path = os.path.join(Config.STORIES_DIR, f"{video_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
