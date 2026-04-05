import asyncio
import base64
import logging
import threading
import time

import cv2
import ollama

from sasayaki.asr.transcriber import Transcriber
from sasayaki.audio.capture import AudioCapture
from sasayaki.audio.vad import VadGate
from sasayaki.config import Config
from sasayaki.llm.profiler import ProfileExtractor
from sasayaki.llm.suggester import ResponseSuggester
from sasayaki.nlp.keyword_extractor import KeywordExtractor
from sasayaki.nlp.wiki import WikiLookup
from sasayaki.types import (
    EntityEvent, ExpressionChangeEvent, FaceAnalysisState,
    PartnerProfile, PipelineState, TranscriptEvent,
)
from sasayaki.vision.face_analyzer import FaceAnalyzer
from sasayaki.vision.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)

EXPLAIN_PROMPT = "以下の用語を1〜2文で簡潔に説明してください。余計な前置きは不要です。"


class Pipeline:
    """Orchestrates the full audio -> transcription -> NLP -> LLM pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.state = PipelineState()
        self._lock = threading.Lock()
        self._llm_task: asyncio.Task | None = None
        self._keyword_task: asyncio.Task | None = None
        self._keyword_processed_texts: list[str] = []
        self._profile_task: asyncio.Task | None = None
        self._profile_processed_idx: int = 0
        self._tasks: list[asyncio.Task] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._system_capture: AudioCapture | None = None
        self._mic_capture: AudioCapture | None = None
        self._face_analyzer: FaceAnalyzer | None = None
        self._screen_capture: ScreenCapture | None = None

    def get_state(self) -> PipelineState:
        with self._lock:
            return PipelineState(
                transcripts=list(self.state.transcripts),
                entities=list(self.state.entities),
                suggestions=list(self.state.suggestions),
                suggesting=self.state.suggesting,
                suggestion_style=self.state.suggestion_style,
                profile=PartnerProfile(
                    name=self.state.profile.name,
                    facts=list(self.state.profile.facts),
                    summary=self.state.profile.summary,
                ),
                profiling=self.state.profiling,
                is_running=self.state.is_running,
                error=self.state.error,
                system_device=self.state.system_device,
                mic_device=self.state.mic_device,
                ollama_ok=self.state.ollama_ok,
                system_level=self._system_capture.level if self._system_capture else 0.0,
                mic_level=self._mic_capture.level if self._mic_capture else 0.0,
                face=FaceAnalysisState(
                    detected=self.state.face.detected,
                    joy=self.state.face.joy,
                    surprise=self.state.face.surprise,
                    concern=self.state.face.concern,
                    neutral=self.state.face.neutral,
                    dominant_emotion=(
                        self.state.face.dominant_emotion
                    ),
                    nodding=self.state.face.nodding,
                    nod_count=self.state.face.nod_count,
                    expression_changes=list(
                        self.state.face.expression_changes
                    ),
                    fps=self.state.face.fps,
                    face_image_base64=(
                        self.state.face.face_image_base64
                    ),
                ),
            )

    def add_manual_keyword(self, term: str):
        """Add a keyword manually from the UI."""
        asyncio.run_coroutine_threadsafe(
            self._lookup_and_add(term),
            self._loop,
        )

    def request_suggestions(self, style: str):
        """Request suggestion generation with a specific style. Called from UI."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._generate_suggestions_styled(style),
            self._loop,
        )

    def request_stop(self):
        """Request the pipeline to stop. Safe to call from any thread."""
        if self._loop is None:
            return
        for task in self._tasks:
            self._loop.call_soon_threadsafe(task.cancel)

    def reset_state(self):
        """Clear all accumulated state for a fresh restart."""
        with self._lock:
            self.state = PipelineState()
        self._llm_task = None
        self._keyword_task = None
        self._keyword_processed_texts = []
        self._profile_task = None
        self._profile_processed_idx = 0
        self._tasks = []

    async def run(self):
        logger.info("Pipeline starting...")
        self._loop = asyncio.get_event_loop()

        # Queues
        system_audio_q: asyncio.Queue = asyncio.Queue(maxsize=100)
        mic_audio_q: asyncio.Queue = asyncio.Queue(maxsize=100)
        system_speech_q: asyncio.Queue = asyncio.Queue(maxsize=10)
        mic_speech_q: asyncio.Queue = asyncio.Queue(maxsize=10)
        transcript_q: asyncio.Queue = asyncio.Queue(maxsize=50)

        # Audio capture
        try:
            self._system_capture = AudioCapture(
                config=self.config, source="system",
                queue=system_audio_q, loop=self._loop,
            )
            self._mic_capture = AudioCapture(
                config=self.config, source="mic",
                queue=mic_audio_q, loop=self._loop,
            )
        except RuntimeError as e:
            logger.error("Audio device error: %s", e)
            with self._lock:
                self.state.error = str(e)
            return

        # VAD
        system_vad = VadGate(
            config=self.config, source="system",
            input_queue=system_audio_q, output_queue=system_speech_q,
        )
        mic_vad = VadGate(
            config=self.config, source="mic",
            input_queue=mic_audio_q, output_queue=mic_speech_q,
        )

        # ASR
        merged_speech_q: asyncio.Queue = asyncio.Queue(maxsize=20)
        transcriber = Transcriber(
            config=self.config,
            input_queue=merged_speech_q, output_queue=transcript_q,
        )

        # NLP & LLM
        self._keyword_extractor = KeywordExtractor(config=self.config)
        self._wiki = WikiLookup(config=self.config)
        self._ollama_client = ollama.AsyncClient()
        self._profiler = ProfileExtractor(config=self.config)
        self._suggester = ResponseSuggester(config=self.config)

        # Check Ollama
        ollama_ok = await self._suggester.health_check()
        if not ollama_ok:
            logger.warning(
                "Ollama not available or model not found. "
                "Suggestions and LLM keyword extraction will be disabled."
            )

        # Face analysis
        self._face_analyzer = FaceAnalyzer()
        self._screen_capture = ScreenCapture(
            monitor=self.config.screen_monitor, fps=10.0
        )

        # Start audio streams
        self._system_capture.start()
        self._mic_capture.start()
        with self._lock:
            self.state.is_running = True
            self.state.system_device = self._system_capture.resolved_device_name
            self.state.mic_device = self._mic_capture.resolved_device_name
            self.state.ollama_ok = ollama_ok

        logger.info("Pipeline running. Listening...")

        self._tasks = [
            asyncio.create_task(system_vad.run(), name="system_vad"),
            asyncio.create_task(mic_vad.run(), name="mic_vad"),
            asyncio.create_task(
                self._merge_queues(system_speech_q, mic_speech_q, merged_speech_q),
                name="merge",
            ),
            asyncio.create_task(transcriber.run(), name="transcriber"),
            asyncio.create_task(
                self._process_transcripts(transcript_q, ollama_ok),
                name="processor",
            ),
            asyncio.create_task(
                self._face_analysis_loop(),
                name="face_analysis",
            ),
        ]

        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
        finally:
            self._system_capture.stop()
            self._mic_capture.stop()
            if self._face_analyzer:
                self._face_analyzer.close()
            if self._screen_capture:
                self._screen_capture.close()
            with self._lock:
                self.state.is_running = False
            logger.info("Pipeline stopped")

    async def _merge_queues(self, q1, q2, out):
        async def forward(src):
            while True:
                item = await src.get()
                await out.put(item)
        await asyncio.gather(forward(q1), forward(q2))

    async def _process_transcripts(
        self,
        transcript_q: asyncio.Queue,
        ollama_ok: bool,
    ):
        while True:
            event: TranscriptEvent = await transcript_q.get()

            # Update transcript state
            with self._lock:
                if (
                    self.state.transcripts
                    and self.state.transcripts[-1].is_partial
                    and self.state.transcripts[-1].source == event.source
                ):
                    self.state.transcripts[-1] = event
                else:
                    self.state.transcripts.append(event)

                if len(self.state.transcripts) > self.config.ui_max_transcript_messages:
                    self.state.transcripts = self.state.transcripts[
                        -self.config.ui_max_transcript_messages:
                    ]

            # Keyword extraction (LLM-based)
            # Collect all transcript text, extract from unprocessed portion
            if ollama_ok and (
                self._keyword_task is None or self._keyword_task.done()
            ):
                with self._lock:
                    all_texts = [t.text for t in self.state.transcripts]
                full_text = "\n".join(all_texts)
                processed = "\n".join(self._keyword_processed_texts)
                # Only extract if there's meaningful new text
                new_text = full_text[len(processed):].strip()
                if len(new_text) >= 20:
                    self._keyword_processed_texts = list(all_texts)
                    self._keyword_task = asyncio.create_task(
                        self._extract_keywords(new_text)
                    )

            # Profile extraction: trigger on final system speech
            if ollama_ok and event.source == "system" and not event.is_partial:
                if self._profile_task is None or self._profile_task.done():
                    self._profile_task = asyncio.create_task(
                        self._extract_profile()
                    )

    async def _face_analysis_loop(self):
        """Periodically capture screen and analyze faces."""
        logger.info("Face analysis loop started")
        loop = asyncio.get_event_loop()
        frame_count = 0
        last_fps_time = time.monotonic()
        fps_frame_count = 0
        current_fps = 0.0
        while True:
            try:
                frame = await loop.run_in_executor(
                    None, self._screen_capture.grab
                )
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue
                frame_count += 1
                fps_frame_count += 1
                face_state = await loop.run_in_executor(
                    None, self._face_analyzer.analyze, frame
                )

                # Calculate FPS every 5 frames
                now = time.monotonic()
                elapsed = now - last_fps_time
                if elapsed >= 2.0:
                    current_fps = fps_frame_count / elapsed
                    fps_frame_count = 0
                    last_fps_time = now

                if frame_count % 10 == 1:
                    logger.info(
                        "Face analysis #%d: detected=%s, "
                        "fps=%.1f",
                        frame_count,
                        face_state.detected,
                        current_fps,
                    )

                # Convert face crop to base64
                face_b64 = ""
                if (face_state.detected
                        and face_state.face_crop is not None):
                    bgr = cv2.cvtColor(
                        face_state.face_crop, cv2.COLOR_RGB2BGR
                    )
                    _, buf = cv2.imencode(".jpg", bgr)
                    face_b64 = base64.b64encode(
                        buf.tobytes()
                    ).decode()

                with self._lock:
                    self.state.face.detected = face_state.detected
                    self.state.face.fps = current_fps
                    self.state.face.face_image_base64 = face_b64
                    if face_state.detected:
                        self.state.face.joy = (
                            face_state.emotions.joy
                        )
                        self.state.face.surprise = (
                            face_state.emotions.surprise
                        )
                        self.state.face.concern = (
                            face_state.emotions.concern
                        )
                        self.state.face.neutral = (
                            face_state.emotions.neutral
                        )
                        self.state.face.dominant_emotion = (
                            face_state.emotions.dominant
                        )
                        self.state.face.nodding = (
                            face_state.nodding
                        )
                        self.state.face.nod_count = (
                            face_state.nod_count
                        )

                        if face_state.expression_changed:
                            snippet = ""
                            if self.state.transcripts:
                                snippet = (
                                    self.state.transcripts[-1]
                                    .text[:50]
                                )
                            self.state.face.expression_changes\
                                .append(
                                    ExpressionChangeEvent(
                                        detail=(
                                            face_state
                                            .expression_change_detail
                                        ),
                                        transcript_snippet=snippet,
                                        timestamp=time.time(),
                                    )
                                )
                            if len(
                                self.state.face
                                .expression_changes
                            ) > 20:
                                self.state.face\
                                    .expression_changes = (
                                        self.state.face
                                        .expression_changes[-20:]
                                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug(
                    "Face analysis frame error", exc_info=True
                )

    async def _extract_keywords(self, text: str):
        """Extract keywords using LLM, then look up definitions."""
        logger.info("Extracting keywords from: %s", text[:80])
        terms = await self._keyword_extractor.extract(text)
        logger.info("Extracted terms: %s", terms)
        if not terms:
            return

        # Look up terms sequentially to avoid Ollama request contention
        for term in terms:
            await self._lookup_and_add(term)

    async def _extract_profile(self):
        """Extract profile facts about the conversation partner from recent speech."""
        await asyncio.sleep(self.config.llm_debounce_sec)

        with self._lock:
            transcripts = list(self.state.transcripts)
            existing_profile = PartnerProfile(
                name=self.state.profile.name,
                facts=list(self.state.profile.facts),
                summary=self.state.profile.summary,
            )
            self.state.profiling = True

        new_transcripts = transcripts[self._profile_processed_idx:]
        self._profile_processed_idx = len(transcripts)

        if not new_transcripts:
            with self._lock:
                self.state.profiling = False
            return

        # Build context with speaker labels
        lines = []
        for t in new_transcripts:
            speaker = "自分" if t.source == "mic" else "相手"
            lines.append(f"{speaker}: 「{t.text}」")
        new_text = "\n".join(lines)

        try:
            facts = await self._profiler.extract(new_text, existing_profile)
            logger.info("Profile facts extracted: %s", [(f.category, f.content) for f in facts])
            if facts:
                with self._lock:
                    for fact in facts:
                        self.state.profile.facts.append(fact)
                        if fact.category == "名前" and not self.state.profile.name:
                            self.state.profile.name = fact.content
                    # Trim to max
                    if len(self.state.profile.facts) > self.config.profile_max_facts:
                        self.state.profile.facts = self.state.profile.facts[
                            -self.config.profile_max_facts:
                        ]

                # Generate summary periodically
                with self._lock:
                    fact_count = len(self.state.profile.facts)
                    profile_copy = PartnerProfile(
                        name=self.state.profile.name,
                        facts=list(self.state.profile.facts),
                        summary=self.state.profile.summary,
                    )
                if fact_count > 0 and fact_count % self.config.profile_summary_interval == 0:
                    summary = await self._profiler.generate_summary(profile_copy)
                    if summary:
                        with self._lock:
                            self.state.profile.summary = summary.strip()
        finally:
            with self._lock:
                self.state.profiling = False

    async def _lookup_and_add(self, term: str):
        """Look up a term: try Wikipedia first, fallback to LLM."""
        # Check duplicate before doing any work
        with self._lock:
            existing = {e.term for e in self.state.entities}
            if term in existing:
                return
            # Add placeholder immediately so UI can show loading state
            self.state.entities.append(EntityEvent(
                term=term,
                definition="",
                timestamp=time.monotonic(),
                loading=True,
            ))
            if len(self.state.entities) > self.config.ui_max_entity_rows:
                self.state.entities = self.state.entities[
                    -self.config.ui_max_entity_rows:
                ]

        definition = await self._wiki.lookup(term)
        source = "wiki"

        if not definition:
            source = "llm"
            try:
                response = await self._ollama_client.chat(
                    model=self.config.ollama_model,
                    messages=[
                        {"role": "system", "content": EXPLAIN_PROMPT},
                        {"role": "user", "content": term},
                    ],
                    options={"temperature": 0.0, "num_predict": 150},
                    think=False,
                )
                msg = response["message"]
                definition = getattr(msg, "content", "") or msg.get("content", "")
            except Exception:
                logger.warning("LLM explain failed for: %s", term)
                # Remove the placeholder on failure
                with self._lock:
                    self.state.entities = [
                        e for e in self.state.entities if e.term != term
                    ]
                return

        if definition:
            logger.info("Keyword added [%s]: %s", source, term)
            with self._lock:
                for e in self.state.entities:
                    if e.term == term:
                        e.definition = definition.strip()
                        e.loading = False
                        break

    async def _generate_suggestions_styled(self, style: str):
        if self._llm_task and not self._llm_task.done():
            self._llm_task.cancel()

        with self._lock:
            self.state.suggesting = True
            self.state.suggestion_style = style
            transcripts = list(self.state.transcripts)

        try:
            suggestions = await self._suggester.suggest(transcripts, style)
            if suggestions:
                with self._lock:
                    self.state.suggestions = suggestions
                    self.state.suggestion_style = style
        finally:
            with self._lock:
                self.state.suggesting = False
