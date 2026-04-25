import asyncio
import json
import logging
import sys
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict

import sounddevice as sd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from sasayaki.audio.capture import list_input_devices
from sasayaki.config import Config
from sasayaki.pipeline.orchestrator import Pipeline

from .schemas import (
    DeviceInfo,
    DevicesResponse,
    KeywordRequest,
    MonitorInfo,
    MonitorsResponse,
    OkResponse,
    PipelineStateSchema,
    ScreenRegionResponse,
    SettingsPatch,
    SuggestRequest,
)

logger = logging.getLogger(__name__)

STATE_TICK_HZ = 10


async def _query_devices_fresh() -> dict[str, list[str]] | None:
    """Re-query audio devices in a child process to bypass PortAudio's
    cached device list. Returns None on failure so callers can fall
    back to the (stale) in-process listing.
    """
    code = (
        "import sounddevice as sd, json, sys\n"
        "json.dump({\n"
        "  'input': [d['name'] for d in sd.query_devices()"
        " if d['max_input_channels'] > 0],\n"
        "  'output': [d['name'] for d in sd.query_devices()"
        " if d['max_output_channels'] > 0],\n"
        "}, sys.stdout)\n"
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), timeout=5.0
        )
    except (asyncio.TimeoutError, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


# Fields whose change cannot be picked up by mutating Config in place,
# because some downstream component captured the value at __init__ time
# (audio devices, ML model handles, LLM client, TTS playback).
COLD_FIELDS: frozenset[str] = frozenset(
    {
        "system_audio_device",
        "mic_device",
        "sample_rate",
        "whisper_model",
        "whisper_language",
        "vad_threshold",
        "vad_min_silence_ms",
        "vad_speech_pad_ms",
        "vad_partial_flush_sec",
        "screen_monitor",
        "maai_enabled",
        "maai_frame_rate",
        "maai_device",
        "tts_enabled",
        "tts_backend",
        "tts_omnivoice_model",
        "tts_omnivoice_instruct",
        "tts_omnivoice_speed",
        "tts_output_device",
        "tts_volume",
        "llm_backend",
        "ollama_model",
        "llamacpp_url",
    }
)


class PipelineManager:
    """Owns the Pipeline lifecycle on a dedicated thread.

    The Pipeline performs blocking ML work (model loading, ASR inference,
    face analysis) that would starve the FastAPI event loop if run in
    process — so it gets its own thread with its own asyncio loop.
    """

    def __init__(self, config: Config):
        self.config = config
        self.pipeline = Pipeline(config)
        self._thread: threading.Thread | None = None

    def _run_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.pipeline.run())
        finally:
            loop.close()

    async def start(self):
        self.pipeline.reset_state()
        self._thread = threading.Thread(
            target=self._run_thread, name="sasayaki-pipeline", daemon=True
        )
        self._thread.start()

    async def stop(self):
        if self._thread is None:
            return
        self.pipeline.request_stop()
        await asyncio.get_event_loop().run_in_executor(
            None, self._thread.join, 5.0
        )
        self._thread = None

    async def restart(self):
        await self.stop()
        # New Pipeline instance drops ML sessions/audio streams cleanly.
        self.pipeline = Pipeline(self.config)
        await self.start()

    def apply_settings(self, patch: SettingsPatch) -> list[str]:
        """Apply a partial Config update. Returns changed field names."""
        changed: list[str] = []
        for field, value in patch.model_dump(exclude_unset=True).items():
            if not hasattr(self.config, field):
                continue
            if getattr(self.config, field) != value:
                setattr(self.config, field, value)
                changed.append(field)
        return changed


def create_app(config: Config | None = None) -> FastAPI:
    manager = PipelineManager(config or Config())

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await manager.start()
        try:
            yield
        finally:
            await manager.stop()

    app = FastAPI(title="sasayaki-api", lifespan=lifespan)

    # During dev the Vite frontend runs on a different origin; in packaged
    # Tauri it loads from tauri://localhost. Both need to hit this server.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.manager = manager

    @app.get("/api/health")
    async def health() -> OkResponse:
        return OkResponse(ok=True)

    @app.get("/api/state", response_model=PipelineStateSchema)
    async def get_state():
        snapshot = manager.pipeline.get_state()
        return PipelineStateSchema.model_validate(asdict(snapshot))

    @app.get("/api/devices", response_model=DevicesResponse)
    async def get_devices():
        fresh = await _query_devices_fresh()
        if fresh is not None:
            return DevicesResponse(
                input_devices=[
                    DeviceInfo(name=n) for n in fresh["input"]
                ],
                output_devices=[
                    DeviceInfo(name=n) for n in fresh["output"]
                ],
            )
        # Fall back to in-process query — stale, but better than nothing
        # if the subprocess fails (e.g. python interpreter missing).
        inputs = [DeviceInfo(name=n) for n in list_input_devices()]
        outputs = [
            DeviceInfo(name=d["name"])
            for d in sd.query_devices()
            if d["max_output_channels"] > 0
        ]
        return DevicesResponse(
            input_devices=inputs, output_devices=outputs
        )

    @app.post("/api/suggest", response_model=OkResponse)
    async def suggest(req: SuggestRequest):
        manager.pipeline.request_suggestions(req.style)
        return OkResponse()

    @app.post("/api/keyword", response_model=OkResponse)
    async def keyword(req: KeywordRequest):
        manager.pipeline.add_manual_keyword(req.term)
        return OkResponse()

    @app.post("/api/replay", response_model=OkResponse)
    async def replay():
        ok = manager.pipeline.request_replay()
        return OkResponse(ok=ok)

    @app.post("/api/stop", response_model=OkResponse)
    async def stop():
        await manager.stop()
        return OkResponse()

    @app.post("/api/restart", response_model=OkResponse)
    async def restart():
        await manager.restart()
        return OkResponse()

    @app.get("/api/monitors", response_model=MonitorsResponse)
    async def get_monitors():
        from sasayaki.vision.screen_capture import ScreenCapture

        items = [
            MonitorInfo(
                index=m["index"],
                width=m["width"],
                height=m["height"],
            )
            for m in ScreenCapture.list_monitors()
        ]
        return MonitorsResponse(monitors=items)

    @app.post(
        "/api/screen_region/select",
        response_model=ScreenRegionResponse,
    )
    async def select_screen_region():
        region = await manager.pipeline.select_screen_region()
        return ScreenRegionResponse(region=region)

    @app.post(
        "/api/screen_region/clear",
        response_model=ScreenRegionResponse,
    )
    async def clear_screen_region():
        manager.pipeline.clear_screen_region()
        return ScreenRegionResponse(region=(0, 0, 0, 0))

    @app.post("/api/settings", response_model=OkResponse)
    async def settings(patch: SettingsPatch):
        changed = manager.apply_settings(patch)
        if not changed:
            return OkResponse()
        cold = [f for f in changed if f in COLD_FIELDS]
        if cold:
            logger.info(
                "Cold settings changed: %s -> restarting pipeline",
                cold,
            )
            await manager.restart()
        else:
            logger.info(
                "Hot settings changed: %s -> applied without restart",
                changed,
            )
        return OkResponse()

    @app.websocket("/ws/state")
    async def ws_state(ws: WebSocket):
        await ws.accept()
        interval = 1.0 / STATE_TICK_HZ
        try:
            while True:
                snapshot = manager.pipeline.get_state()
                payload = PipelineStateSchema.model_validate(
                    asdict(snapshot)
                )
                await ws.send_json(
                    {"type": "state", "payload": payload.model_dump()}
                )
                await asyncio.sleep(interval)
        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")
        except Exception:
            logger.exception("WebSocket handler crashed")

    return app
