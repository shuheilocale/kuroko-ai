import asyncio
import logging
import threading
import time

import ollama

from sasayaki.asr.transcriber import Transcriber
from sasayaki.audio.capture import AudioCapture
from sasayaki.audio.vad import VadGate
from sasayaki.config import Config
from sasayaki.llm.suggester import ResponseSuggester
from sasayaki.nlp.keyword_extractor import KeywordExtractor
from sasayaki.nlp.wiki import WikiLookup
from sasayaki.types import EntityEvent, PipelineState, TranscriptEvent

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

    def get_state(self) -> PipelineState:
        with self._lock:
            return PipelineState(
                transcripts=list(self.state.transcripts),
                entities=list(self.state.entities),
                suggestions=list(self.state.suggestions),
                is_running=self.state.is_running,
                error=self.state.error,
                system_device=self.state.system_device,
                mic_device=self.state.mic_device,
                ollama_ok=self.state.ollama_ok,
            )

    def add_manual_keyword(self, term: str):
        """Add a keyword manually from the UI."""
        asyncio.run_coroutine_threadsafe(
            self._lookup_and_add(term),
            self._loop,
        )

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
            system_capture = AudioCapture(
                config=self.config, source="system",
                queue=system_audio_q, loop=self._loop,
            )
            mic_capture = AudioCapture(
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
        suggester = ResponseSuggester(config=self.config)

        # Check Ollama
        ollama_ok = await suggester.health_check()
        if not ollama_ok:
            logger.warning(
                "Ollama not available or model not found. "
                "Suggestions and LLM keyword extraction will be disabled."
            )

        # Start audio streams
        system_capture.start()
        mic_capture.start()
        with self._lock:
            self.state.is_running = True
            self.state.system_device = system_capture.resolved_device_name
            self.state.mic_device = mic_capture.resolved_device_name
            self.state.ollama_ok = ollama_ok

        logger.info("Pipeline running. Listening...")

        tasks = [
            asyncio.create_task(system_vad.run(), name="system_vad"),
            asyncio.create_task(mic_vad.run(), name="mic_vad"),
            asyncio.create_task(
                self._merge_queues(system_speech_q, mic_speech_q, merged_speech_q),
                name="merge",
            ),
            asyncio.create_task(transcriber.run(), name="transcriber"),
            asyncio.create_task(
                self._process_transcripts(transcript_q, suggester, ollama_ok),
                name="processor",
            ),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            system_capture.stop()
            mic_capture.stop()
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
        suggester: ResponseSuggester,
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

            # LLM suggestion: trigger on final system (opponent) speech
            if ollama_ok and event.source == "system" and not event.is_partial:
                if self._llm_task and not self._llm_task.done():
                    self._llm_task.cancel()
                self._llm_task = asyncio.create_task(
                    self._generate_suggestions(suggester)
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

    async def _lookup_and_add(self, term: str):
        """Look up a term: try Wikipedia first, fallback to LLM."""
        # Check duplicate before doing any work
        with self._lock:
            existing = {e.term for e in self.state.entities}
            if term in existing:
                return

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
                return

        if definition:
            logger.info("Keyword added [%s]: %s", source, term)
            with self._lock:
                self.state.entities.append(EntityEvent(
                    term=term,
                    definition=definition.strip(),
                    timestamp=time.monotonic(),
                ))
                if len(self.state.entities) > self.config.ui_max_entity_rows:
                    self.state.entities = self.state.entities[
                        -self.config.ui_max_entity_rows:
                    ]

    async def _generate_suggestions(self, suggester: ResponseSuggester):
        await asyncio.sleep(self.config.llm_debounce_sec)

        with self._lock:
            transcripts = list(self.state.transcripts)

        suggestions = await suggester.suggest(transcripts)
        if suggestions:
            with self._lock:
                self.state.suggestions = suggestions
