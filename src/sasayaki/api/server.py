import asyncio
import logging
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
    OkResponse,
    PipelineStateSchema,
    SettingsPatch,
    SuggestRequest,
)

logger = logging.getLogger(__name__)

STATE_TICK_HZ = 10


class PipelineManager:
    """Owns the Pipeline lifecycle on a dedicated thread.

    The Pipeline performs blocking ML work (model loading, ASR inference,
    face analysis) that would starve the FastAPI event loop if run in
    process. Mirrors the threading pattern used by the legacy NiceGUI
    entry point.
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
        inputs = [DeviceInfo(name=n) for n in list_input_devices()]
        outputs = [
            DeviceInfo(name=d["name"])
            for d in sd.query_devices()
            if d["max_output_channels"] > 0
        ]
        return DevicesResponse(input_devices=inputs, output_devices=outputs)

    @app.post("/api/suggest", response_model=OkResponse)
    async def suggest(req: SuggestRequest):
        manager.pipeline.request_suggestions(req.style)
        return OkResponse()

    @app.post("/api/keyword", response_model=OkResponse)
    async def keyword(req: KeywordRequest):
        manager.pipeline.add_manual_keyword(req.term)
        return OkResponse()

    @app.post("/api/stop", response_model=OkResponse)
    async def stop():
        await manager.stop()
        return OkResponse()

    @app.post("/api/restart", response_model=OkResponse)
    async def restart():
        await manager.restart()
        return OkResponse()

    @app.post("/api/settings", response_model=OkResponse)
    async def settings(patch: SettingsPatch):
        changed = manager.apply_settings(patch)
        if changed:
            logger.info("Settings changed: %s -> restarting pipeline", changed)
            await manager.restart()
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
