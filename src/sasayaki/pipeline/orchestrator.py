import asyncio
import logging
import threading
import time

from sasayaki.asr.transcriber import Transcriber
from sasayaki.audio.capture import AudioCapture
from sasayaki.audio.vad import VadGate
from sasayaki.config import Config
from sasayaki.llm.suggester import ResponseSuggester
from sasayaki.nlp.ner import EntityExtractor
from sasayaki.nlp.wiki import WikiLookup
from sasayaki.types import EntityEvent, PipelineState, TranscriptEvent

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the full audio -> transcription -> NLP -> LLM pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.state = PipelineState()
        self._lock = threading.Lock()
        self._llm_task: asyncio.Task | None = None

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

    async def run(self):
        logger.info("Pipeline starting...")
        loop = asyncio.get_event_loop()

        # Queues
        system_audio_q: asyncio.Queue = asyncio.Queue(maxsize=100)
        mic_audio_q: asyncio.Queue = asyncio.Queue(maxsize=100)
        system_speech_q: asyncio.Queue = asyncio.Queue(maxsize=10)
        mic_speech_q: asyncio.Queue = asyncio.Queue(maxsize=10)
        transcript_q: asyncio.Queue = asyncio.Queue(maxsize=50)

        # Audio capture
        try:
            system_capture = AudioCapture(config=self.config, source="system", queue=system_audio_q, loop=loop)
            mic_capture = AudioCapture(config=self.config, source="mic", queue=mic_audio_q, loop=loop)
        except RuntimeError as e:
            logger.error("Audio device error: %s", e)
            with self._lock:
                self.state.error = str(e)
            return

        # VAD
        system_vad = VadGate(config=self.config, source="system", input_queue=system_audio_q, output_queue=system_speech_q)
        mic_vad = VadGate(config=self.config, source="mic", input_queue=mic_audio_q, output_queue=mic_speech_q)

        # ASR - merge both speech queues into a single transcriber queue
        merged_speech_q: asyncio.Queue = asyncio.Queue(maxsize=20)
        transcriber = Transcriber(config=self.config, input_queue=merged_speech_q, output_queue=transcript_q)

        # NLP & LLM
        ner = EntityExtractor(config=self.config)
        wiki = WikiLookup(config=self.config)
        suggester = ResponseSuggester(config=self.config)

        # Check Ollama
        ollama_ok = await suggester.health_check()
        if not ollama_ok:
            logger.warning("Ollama not available or model not found. Suggestions will be disabled.")

        # Start audio streams
        system_capture.start()
        mic_capture.start()
        with self._lock:
            self.state.is_running = True
            self.state.system_device = system_capture.resolved_device_name
            self.state.mic_device = mic_capture.resolved_device_name
            self.state.ollama_ok = ollama_ok

        logger.info("Pipeline running. Listening...")

        # Launch async tasks
        tasks = [
            asyncio.create_task(system_vad.run(), name="system_vad"),
            asyncio.create_task(mic_vad.run(), name="mic_vad"),
            asyncio.create_task(self._merge_queues(system_speech_q, mic_speech_q, merged_speech_q), name="merge"),
            asyncio.create_task(transcriber.run(), name="transcriber"),
            asyncio.create_task(self._process_transcripts(transcript_q, ner, wiki, suggester, ollama_ok), name="processor"),
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

    async def _merge_queues(self, q1: asyncio.Queue, q2: asyncio.Queue, out: asyncio.Queue):
        """Merge two speech segment queues into one."""
        async def forward(src):
            while True:
                item = await src.get()
                await out.put(item)

        await asyncio.gather(
            forward(q1),
            forward(q2),
        )

    async def _process_transcripts(
        self,
        transcript_q: asyncio.Queue,
        ner: EntityExtractor,
        wiki: WikiLookup,
        suggester: ResponseSuggester,
        ollama_ok: bool,
    ):
        """Process transcript events: update state, run NER, trigger LLM."""
        while True:
            event: TranscriptEvent = await transcript_q.get()

            # Update transcript state
            with self._lock:
                if event.is_partial:
                    # Replace last partial from same source, if any
                    if (
                        self.state.transcripts
                        and self.state.transcripts[-1].is_partial
                        and self.state.transcripts[-1].source == event.source
                    ):
                        self.state.transcripts[-1] = event
                    else:
                        self.state.transcripts.append(event)
                else:
                    # Replace last partial from same source with final
                    if (
                        self.state.transcripts
                        and self.state.transcripts[-1].is_partial
                        and self.state.transcripts[-1].source == event.source
                    ):
                        self.state.transcripts[-1] = event
                    else:
                        self.state.transcripts.append(event)

                # Trim to max
                if len(self.state.transcripts) > self.config.ui_max_transcript_messages:
                    self.state.transcripts = self.state.transcripts[-self.config.ui_max_transcript_messages:]

            # NER + Wikipedia (fire and forget for non-blocking)
            asyncio.create_task(self._process_entities(event.text, ner, wiki))

            # LLM suggestion: trigger on final system (opponent) speech
            if ollama_ok and event.source == "system" and not event.is_partial:
                # Debounce: cancel previous pending LLM task
                if self._llm_task and not self._llm_task.done():
                    self._llm_task.cancel()
                self._llm_task = asyncio.create_task(
                    self._generate_suggestions(suggester, event.text)
                )

    async def _process_entities(self, text: str, ner: EntityExtractor, wiki: WikiLookup):
        """Extract entities and look them up on Wikipedia."""
        terms = await ner.extract(text)
        for term in terms:
            definition = await wiki.lookup(term)
            if definition:
                entity = EntityEvent(
                    term=term,
                    definition=definition,
                    timestamp=time.monotonic(),
                )
                with self._lock:
                    self.state.entities.append(entity)
                    if len(self.state.entities) > self.config.ui_max_entity_rows:
                        self.state.entities = self.state.entities[-self.config.ui_max_entity_rows:]

    async def _generate_suggestions(self, suggester: ResponseSuggester, trigger_text: str):
        """Generate LLM suggestions with debounce."""
        # Wait for debounce period
        await asyncio.sleep(self.config.llm_debounce_sec)

        with self._lock:
            transcripts = list(self.state.transcripts)

        suggestions = await suggester.suggest(transcripts)
        if suggestions:
            with self._lock:
                self.state.suggestions = suggestions
