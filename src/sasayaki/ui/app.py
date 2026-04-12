import asyncio
import logging
import subprocess
import tempfile
import threading
from datetime import datetime, timezone, timedelta
from itertools import groupby
from pathlib import Path

from nicegui import ui

import sounddevice as sd

from sasayaki.audio.capture import list_input_devices
from sasayaki.config import Config
from sasayaki.llm.client import LLMClient
from sasayaki.pipeline.orchestrator import Pipeline
from sasayaki.vision.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)

STYLE_BUTTONS = {
    "深堀り": "indigo",
    "褒める": "pink",
    "批判的": "red",
    "矛盾指摘": "orange",
    "よいしょ": "amber",
    "共感": "teal",
    "まとめる": "blue-grey",
    "話題転換": "green",
    "具体例を求める": "cyan",
    "ボケる": "purple",
    "謝罪": "deep-orange",
    "知識でマウント": "brown",
}


class NiceGuiApp:
    """NiceGUI UI for the meeting assistant."""

    def __init__(self, config: Config):
        self.config = config
        self.pipeline = Pipeline(config)
        self._pipeline_thread: threading.Thread | None = None

    def _start_pipeline(self):
        self.pipeline.reset_state()
        loop = asyncio.new_event_loop()

        def run():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.pipeline.run())

        self._pipeline_thread = threading.Thread(
            target=run, daemon=True
        )
        self._pipeline_thread.start()

    def _restart_pipeline(self):
        self.pipeline.request_stop()
        if self._pipeline_thread:
            self._pipeline_thread.join(timeout=5)
        self._start_pipeline()

    def build(self) -> None:
        @ui.page("/")
        def index():
            ui.add_head_html("""
<style>
.transcript-scroll {
    height: calc(100vh - 520px);
    min-height: 250px;
    max-height: 600px;
    overflow-y: auto;
}
.suggest-scroll {
    height: calc(100vh - 660px);
    min-height: 150px;
    max-height: 450px;
    overflow-y: auto;
}
.scroll-box {
    max-height: 220px;
    overflow-y: auto;
}
.chat-msg {
    padding: 4px 10px;
    border-radius: 10px;
    margin: 1px 0;
    max-width: 90%;
    font-size: 0.9em;
}
.chat-mic {
    background: #e3f2fd;
    align-self: flex-end;
}
.chat-system {
    background: #f3e5f5;
    align-self: flex-start;
}
.chat-partial { font-style: italic; opacity: 0.7; }
.profile-name {
    font-size: 1.1em;
    font-weight: bold;
    margin-bottom: 4px;
}
.profile-category {
    font-weight: 600;
    color: #1565c0;
    margin-top: 4px;
    font-size: 0.9em;
}
.profile-fact {
    padding: 1px 0 1px 10px;
    border-left: 2px solid #e0e0e0;
    margin: 1px 0;
    font-size: 0.85em;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.loading-pulse {
    animation: pulse 1.5s ease-in-out infinite;
    color: #888;
}
@keyframes dot-blink {
    0% { content: ''; }
    25% { content: '.'; }
    50% { content: '..'; }
    75% { content: '...'; }
}
.loading-dots::after {
    content: '';
    animation: dot-blink 1.2s steps(1) infinite;
}
.compact-card .q-card__section {
    padding: 8px 12px;
}
.auto-mode-badge {
    background: #ff9800;
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75em;
    font-weight: bold;
}
.manual-mode-badge {
    background: #1976d2;
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75em;
    font-weight: bold;
}
</style>
            """)

            # ── Header: title + meters + status ──
            with ui.row().classes(
                "w-full items-center gap-4"
            ):
                ui.label(
                    "ささやき女将"
                ).classes("text-xl font-bold")
                ui.label("Sys:").classes("text-xs")
                system_level_bar = ui.linear_progress(
                    value=0, show_value=False
                ).props("color=purple").classes("w-24")
                ui.label("Mic:").classes("text-xs")
                mic_level_bar = ui.linear_progress(
                    value=0, show_value=False
                ).props("color=blue").classes("w-24")
                ui.label("TT:").classes("text-xs")
                tt_now_bar = ui.linear_progress(
                    value=0, show_value=False
                ).props("color=orange").classes("w-20")
                tt_now_label = ui.label("--").classes(
                    "text-xs"
                )
                tt_future_bar = ui.linear_progress(
                    value=0, show_value=False
                ).props("color=yellow").classes("w-20")
                tt_future_label = ui.label("--").classes(
                    "text-xs"
                )
                tt_indicator = ui.label("").classes(
                    "text-sm"
                )
                tts_label = ui.label("").classes(
                    "text-sm text-purple-600"
                )
                status_label = ui.markdown(
                    "**Status:** 起動中..."
                ).classes("text-xs")

            # ── Collapsible settings ──
            devices = list_input_devices()
            monitors = ScreenCapture.list_monitors()
            monitor_options = {
                m["index"]: (
                    f"Monitor {m['index']}"
                    f" ({m['width']}x{m['height']})"
                )
                for m in monitors
            }
            ollama_models = (
                LLMClient.list_ollama_models()
            )
            backend_options = {
                "ollama": "Ollama",
                "llamacpp": "llama.cpp",
            }
            output_devices = [
                dev["name"]
                for dev in sd.query_devices()
                if dev["max_output_channels"] > 0
            ]

            with ui.expansion(
                "設定", icon="settings"
            ).classes("w-full").props("dense"):
                with ui.row().classes(
                    "w-full items-center gap-3 "
                    "flex-wrap"
                ):
                    system_select = ui.select(
                        devices,
                        value=(
                            self.config
                            .system_audio_device
                        ),
                        label="System Audio",
                    ).classes("w-40")
                    mic_select = ui.select(
                        devices,
                        value=self.config.mic_device,
                        label="Mic",
                    ).classes("w-40")
                    monitor_select = ui.select(
                        monitor_options,
                        value=1,
                        label="Screen",
                    ).classes("w-44")
                    backend_select = ui.select(
                        backend_options,
                        value=self.config.llm_backend,
                        label="LLM",
                    ).classes("w-32")
                    model_select = ui.select(
                        ollama_models or {
                            "gemma4:e2b": "gemma4:e2b"
                        },
                        value=self.config.ollama_model,
                        label="Model",
                    ).classes("w-56")
                    llamacpp_url_input = ui.input(
                        label="llama.cpp URL",
                        value=self.config.llamacpp_url,
                    ).classes("w-48")

                    def on_backend_change():
                        is_ollama = (
                            backend_select.value
                            == "ollama"
                        )
                        model_select.set_visibility(
                            is_ollama
                        )
                        llamacpp_url_input.set_visibility(
                            not is_ollama
                        )

                    backend_select.on_value_change(
                        on_backend_change
                    )
                    on_backend_change()

                with ui.row().classes(
                    "w-full items-center gap-3 "
                    "flex-wrap"
                ):
                    maai_toggle = ui.switch(
                        "Turn-Taking",
                        value=self.config.maai_enabled,
                    )
                    tts_toggle = ui.switch(
                        "TTS",
                        value=self.config.tts_enabled,
                    )
                    tts_device_select = ui.select(
                        output_devices,
                        value=(
                            self.config.tts_output_device
                            or (
                                output_devices[0]
                                if output_devices
                                else ""
                            )
                        ),
                        label="TTS出力先",
                    ).classes("w-44")
                    region_label = ui.label(
                        "キャプチャ: 全画面"
                    ).classes("text-sm")

                    async def select_region():
                        region_label.set_text(
                            "キャプチャ: 選択中..."
                        )
                        result = (
                            await
                            self._select_screen_region()
                        )
                        if result:
                            x, y, w, h = result
                            sc = (
                                self.pipeline
                                ._screen_capture
                            )
                            if sc:
                                sc.region = (
                                    x, y, w, h
                                )
                            region_label.set_text(
                                f"キャプチャ: "
                                f"{w}x{h} ({x},{y})"
                            )
                        else:
                            region_label.set_text(
                                "キャプチャ: 全画面"
                            )

                    ui.button(
                        "範囲選択",
                        on_click=select_region,
                    ).props("dense flat size=sm")
                    ui.button(
                        "全画面",
                        on_click=lambda: (
                            setattr(
                                self.pipeline
                                ._screen_capture,
                                "region",
                                (0, 0, 0, 0),
                            )
                            if (
                                self.pipeline
                                ._screen_capture
                            )
                            else None,
                            region_label.set_text(
                                "キャプチャ: 全画面"
                            ),
                        ),
                    ).props("dense flat size=sm")

                    def on_apply():
                        self.config.system_audio_device = (
                            system_select.value
                        )
                        self.config.mic_device = (
                            mic_select.value
                        )
                        self.config.screen_monitor = (
                            monitor_select.value
                        )
                        self.config.llm_backend = (
                            backend_select.value
                        )
                        self.config.ollama_model = (
                            model_select.value
                        )
                        self.config.llamacpp_url = (
                            llamacpp_url_input.value
                        )
                        self.config.maai_enabled = (
                            maai_toggle.value
                        )
                        self.config.tts_enabled = (
                            tts_toggle.value
                        )
                        self.config.tts_output_device = (
                            tts_device_select.value
                        )
                        self._restart_pipeline()
                        ui.notify(
                            "設定を適用しました",
                            type="info",
                        )

                    ui.button(
                        "適用", on_click=on_apply
                    ).props("dense color=primary")

            # ══════════════════════════════════════
            # Upper row: Transcript (big) + Suggestions
            # ══════════════════════════════════════
            with ui.grid(columns="3fr 2fr").classes(
                "w-full gap-2"
            ):
                # ── Transcript ──
                with ui.card().classes(
                    "w-full compact-card"
                ):
                    ui.label("文字起こし").classes(
                        "text-sm font-semibold"
                    )
                    transcript_container = (
                        ui.column().classes(
                            "transcript-scroll w-full"
                        ).props(
                            'id="transcript-scroll"'
                        )
                    )

                # ── Suggestions ──
                with ui.card().classes(
                    "w-full compact-card"
                ):
                    # Header: title + auto mode
                    with ui.row().classes(
                        "w-full items-center gap-2"
                    ):
                        ui.label("応答候補").classes(
                            "text-sm font-semibold"
                        )
                        suggest_mode_badge = ui.html(
                            ""
                        )

                    # Auto-suggest mode selector
                    with ui.row().classes(
                        "w-full items-center gap-2"
                    ):
                        ui.label(
                            "自動ささやきモード:"
                        ).classes("text-xs")
                        auto_style_select = ui.select(
                            list(STYLE_BUTTONS.keys()),
                            value=(
                                self.config
                                .auto_suggest_style
                            ),
                        ).props("dense").classes(
                            "w-28"
                        )

                        def on_auto_style(e):
                            self.config.auto_suggest_style = (
                                e.value
                            )

                        auto_style_select.on_value_change(
                            on_auto_style
                        )

                    # Manual style buttons
                    with ui.row().classes(
                        "w-full flex-wrap gap-1"
                    ):
                        for style, color in (
                            STYLE_BUTTONS.items()
                        ):
                            ui.button(
                                style,
                                on_click=(
                                    lambda s=style: (
                                        self.pipeline
                                        .request_suggestions(
                                            s
                                        )
                                    )
                                ),
                            ).props(
                                f"color={color} "
                                "dense"
                            )

                    suggestions_container = (
                        ui.column().classes(
                            "suggest-scroll w-full"
                        )
                    )

            # ══════════════════════════════════════
            # Lower row: Keywords + Profile + Face
            # ══════════════════════════════════════
            with ui.grid(columns="1fr 1fr 1fr").classes(
                "w-full gap-2"
            ):
                # ── Keywords ──
                with ui.card().classes(
                    "w-full compact-card"
                ):
                    ui.label("キーワード").classes(
                        "text-sm font-semibold"
                    )
                    with ui.row().classes(
                        "w-full items-center"
                    ):
                        keyword_input = ui.input(
                            placeholder="用語を検索..."
                        ).classes(
                            "flex-grow"
                        ).props("dense")
                        ui.button(
                            "検索",
                            on_click=lambda: (
                                self._add_keyword(
                                    keyword_input
                                )
                            ),
                        ).props("dense flat size=sm")
                    keyword_input.on(
                        "keydown.enter",
                        lambda: self._add_keyword(
                            keyword_input
                        ),
                    )
                    keywords_container = (
                        ui.column().classes(
                            "scroll-box w-full"
                        ).props(
                            'id="keywords-scroll"'
                        )
                    )

                # ── Profile ──
                with ui.card().classes(
                    "w-full compact-card"
                ):
                    ui.label(
                        "相手のプロフィール"
                    ).classes("text-sm font-semibold")
                    profile_container = (
                        ui.column().classes(
                            "scroll-box w-full"
                        )
                    )

                # ── Face Analysis ──
                with ui.card().classes(
                    "w-full compact-card"
                ):
                    ui.label("表情分析").classes(
                        "text-sm font-semibold"
                    )
                    with ui.row().classes(
                        "w-full gap-3 items-start"
                    ):
                        with ui.column().classes(
                            "gap-0"
                        ):
                            EMOTION_LABELS = {
                                "joy": ("喜", "amber"),
                                "surprise": (
                                    "驚", "cyan"
                                ),
                                "concern": (
                                    "困", "red"
                                ),
                                "neutral": (
                                    "平", "grey"
                                ),
                            }
                            emotion_bars = {}
                            for key, (
                                label, color
                            ) in (
                                EMOTION_LABELS.items()
                            ):
                                with ui.row().classes(
                                    "items-center gap-1"
                                ):
                                    ui.label(
                                        label
                                    ).classes(
                                        "text-xs w-6"
                                    )
                                    bar = (
                                        ui.linear_progress(
                                            value=0,
                                            show_value=False,
                                        )
                                        .props(
                                            "color="
                                            f"{color}"
                                        )
                                        .classes("w-16")
                                    )
                                    emotion_bars[
                                        key
                                    ] = bar
                        with ui.column().classes(
                            "gap-1 items-center"
                        ):
                            face_image_html = ui.html(
                                '<div style='
                                '"width:48px;'
                                "height:48px;"
                                "background:#eee;"
                                'border-radius:6px">'
                                "</div>"
                            )
                            face_status_label = (
                                ui.label(
                                    "顔未検出"
                                ).classes(
                                    "text-xs "
                                    "text-gray-400"
                                )
                            )
                            nod_label = ui.label(
                                "うなずき: 0"
                            ).classes("text-xs")
                            fps_label = ui.label(
                                "FPS: --"
                            ).classes(
                                "text-xs "
                                "text-gray-400"
                            )
                        with ui.column().classes(
                            "flex-grow"
                        ):
                            ui.label(
                                "表情変化"
                            ).classes(
                                "text-xs "
                                "font-semibold"
                            )
                            expression_log = (
                                ui.column().classes(
                                    "max-h-16 "
                                    "overflow-y-auto"
                                )
                            )

            # ── Polling ──
            jst = timezone(timedelta(hours=9))

            def poll():
                state = self.pipeline.get_state()

                # Transcripts
                transcript_container.clear()
                with transcript_container:
                    for t in state.transcripts:
                        css = (
                            "chat-msg chat-mic"
                            if t.source == "mic"
                            else "chat-msg chat-system"
                        )
                        if t.is_partial:
                            css += " chat-partial"
                        ts = datetime.fromtimestamp(
                            t.timestamp, tz=jst
                        ).strftime("%H:%M:%S")
                        align = (
                            "w-full items-center "
                            "justify-end gap-1"
                            if t.source == "mic"
                            else
                            "w-full items-center "
                            "justify-start gap-1"
                        )
                        with ui.row().classes(align):
                            if t.source != "mic":
                                ui.label(ts).classes(
                                    "text-xs "
                                    "text-gray-400"
                                )
                            ui.label(
                                t.text
                            ).classes(css)
                            if t.source == "mic":
                                ui.label(ts).classes(
                                    "text-xs "
                                    "text-gray-400"
                                )

                # Auto-scroll transcript
                if state.transcripts:
                    ui.run_javascript(
                        'var el=document'
                        '.getElementById('
                        '"transcript-scroll");'
                        "if(el)el.scrollTop="
                        "el.scrollHeight;"
                    )

                # Entities
                if state.entities:
                    keywords_container.clear()
                    with keywords_container:
                        for e in state.entities:
                            if e.loading:
                                with ui.row().classes(
                                    "items-center "
                                    "gap-2 "
                                    "loading-pulse"
                                ):
                                    ui.spinner(
                                        size="sm"
                                    )
                                    ui.label(
                                        e.term
                                    ).classes(
                                        "font-bold "
                                        "text-sm"
                                    )
                            else:
                                ui.markdown(
                                    f"**{e.term}**"
                                    "\n"
                                    f"{e.definition}"
                                ).classes("text-sm")
                                ui.separator()
                else:
                    keywords_container.clear()
                    with keywords_container:
                        ui.label(
                            "キーワードを検出中..."
                        ).classes(
                            "text-gray-400 "
                            "italic text-sm"
                        )

                # Auto-scroll keywords
                if state.entities:
                    ui.run_javascript(
                        'var el=document'
                        '.getElementById('
                        '"keywords-scroll");'
                        "if(el)el.scrollTop="
                        "el.scrollHeight;"
                    )

                # Profile
                profile_container.clear()
                with profile_container:
                    profile = state.profile
                    if profile.name:
                        ui.label(
                            profile.name
                        ).classes("profile-name")
                    if profile.summary:
                        ui.label(
                            profile.summary
                        ).classes(
                            "text-xs "
                            "text-gray-600 italic"
                        )
                        ui.separator()
                    if profile.facts:
                        sorted_facts = sorted(
                            profile.facts,
                            key=lambda f: f.category,
                        )
                        for cat, grp in groupby(
                            sorted_facts,
                            key=lambda f: f.category,
                        ):
                            ui.label(cat).classes(
                                "profile-category"
                            )
                            for fact in grp:
                                ui.label(
                                    f"  {fact.content}"
                                ).classes(
                                    "profile-fact"
                                )
                    elif state.profiling:
                        with ui.row().classes(
                            "items-center gap-2 "
                            "loading-pulse"
                        ):
                            ui.spinner(size="sm")
                            ui.label(
                                "分析中"
                            ).classes(
                                "text-sm "
                                "loading-dots"
                            )
                    else:
                        ui.label(
                            "プロフィール構築中..."
                        ).classes(
                            "text-gray-400 "
                            "italic text-sm"
                        )

                # Suggestions + mode badge
                is_auto = (
                    state.suggestion_style
                    .startswith("[自動]")
                )
                if is_auto:
                    suggest_mode_badge.set_content(
                        '<span class='
                        '"auto-mode-badge">'
                        "自動</span>"
                    )
                elif state.suggesting:
                    suggest_mode_badge.set_content(
                        '<span class='
                        '"manual-mode-badge">'
                        "手動</span>"
                    )
                elif state.suggestions:
                    badge_cls = (
                        "auto-mode-badge"
                        if "[自動]"
                        in state.suggestion_style
                        else "manual-mode-badge"
                    )
                    suggest_mode_badge.set_content(
                        f'<span class="{badge_cls}">'
                        f"{state.suggestion_style}"
                        "</span>"
                    )
                else:
                    suggest_mode_badge.set_content("")

                suggestions_container.clear()
                with suggestions_container:
                    if state.suggesting:
                        with ui.row().classes(
                            "items-center gap-2 "
                            "loading-pulse"
                        ):
                            ui.spinner(size="sm")
                            ui.label(
                                f"「"
                                f"{state.suggestion_style}"
                                f"」で生成中"
                            ).classes(
                                "text-sm "
                                "loading-dots"
                            )
                    elif state.suggestions:
                        ui.markdown(
                            "\n\n".join(
                                f"**{i+1}.** {s}"
                                for i, s in enumerate(
                                    state.suggestions
                                )
                            )
                        ).classes("text-sm")

                # Audio levels
                system_level_bar.set_value(
                    state.system_level
                )
                mic_level_bar.set_value(
                    state.mic_level
                )

                # Turn-taking
                tt = state.turn_taking
                if tt.enabled:
                    tt_now_bar.set_value(tt.p_now)
                    tt_future_bar.set_value(
                        tt.p_future
                    )
                    tt_now_label.set_text(
                        f"{tt.p_now:.2f}"
                    )
                    tt_future_label.set_text(
                        f"{tt.p_future:.2f}"
                    )
                    if tt.is_turn_change:
                        tt_indicator.set_text(
                            "話し終わりそう!"
                        )
                        tt_indicator.classes(
                            add=(
                                "text-orange-600 "
                                "font-bold"
                            ),
                        )
                    else:
                        tt_indicator.set_text("")
                        tt_indicator.classes(
                            remove=(
                                "text-orange-600 "
                                "font-bold"
                            ),
                        )

                # TTS
                if state.tts_playing:
                    tts_label.set_text(
                        "ささやき中..."
                    )
                else:
                    tts_label.set_text("")

                # Face analysis
                face = state.face
                emotion_bars["joy"].set_value(
                    face.joy
                )
                emotion_bars["surprise"].set_value(
                    face.surprise
                )
                emotion_bars["concern"].set_value(
                    face.concern
                )
                emotion_bars["neutral"].set_value(
                    face.neutral
                )
                fps_label.set_text(
                    f"FPS: {face.fps:.1f}"
                )
                if face.detected:
                    DOMINANT_JP = {
                        "joy": "喜び",
                        "surprise": "驚き",
                        "concern": "困惑",
                        "neutral": "平常",
                    }
                    dominant = DOMINANT_JP.get(
                        face.dominant_emotion,
                        face.dominant_emotion,
                    )
                    face_status_label.set_text(
                        f"検出 — {dominant}"
                    )
                    face_status_label.classes(
                        remove="text-gray-400",
                        add="text-green-600",
                    )
                    if face.face_image_base64:
                        face_image_html.set_content(
                            '<img src='
                            '"data:image/'
                            "jpeg;base64,"
                            f"{face.face_image_base64}"
                            '" style='
                            '"width:48px;'
                            "height:48px;"
                            "object-fit:cover;"
                            'border-radius:6px">'
                        )
                else:
                    face_status_label.set_text(
                        "顔未検出"
                    )
                    face_status_label.classes(
                        remove="text-green-600",
                        add="text-gray-400",
                    )
                    face_image_html.set_content(
                        '<div style='
                        '"width:48px;'
                        "height:48px;"
                        "background:#eee;"
                        'border-radius:6px">'
                        "</div>"
                    )
                nod_label.set_text(
                    f"うなずき: {face.nod_count}"
                )
                expression_log.clear()
                with expression_log:
                    for evt in reversed(
                        face.expression_changes[-5:]
                    ):
                        ts = datetime.fromtimestamp(
                            evt.timestamp, tz=jst
                        ).strftime("%H:%M:%S")
                        ui.label(
                            f"{ts} {evt.detail}"
                        ).classes("text-xs")

                # Status
                if state.error:
                    status_label.set_content(
                        f"**Error:** {state.error}"
                    )
                elif state.is_running:
                    ok = (
                        "OK" if state.ollama_ok
                        else "NG"
                    )
                    status_label.set_content(
                        f"**Ollama:** {ok} | "
                        f"発話:"
                        f"{len(state.transcripts)} "
                        f"KW:{len(state.entities)} "
                        f"Prof:"
                        f"{len(state.profile.facts)}"
                    )
                else:
                    status_label.set_content(
                        "**Status:** 停止中"
                    )

            ui.timer(0.5, poll)

    def launch(self) -> None:
        self._start_pipeline()
        ui.run(
            host="127.0.0.1",
            port=7860,
            title="ささやき女将 - AI Meeting Assistant",
            reload=False,
        )

    async def _select_screen_region(
        self,
    ) -> tuple[int, int, int, int] | None:
        loop = asyncio.get_event_loop()

        def _select():
            import cv2

            sc = self.pipeline._screen_capture
            if not sc:
                return None
            mon_w, mon_h = sc.get_monitor_size()
            tmp_sel = tempfile.mktemp(suffix=".png")
            tmp_full = tempfile.mktemp(suffix=".png")
            try:
                subprocess.run(
                    ["screencapture", "-x", tmp_full],
                    timeout=10,
                )
                ret = subprocess.run(
                    ["screencapture", "-i", "-s",
                     tmp_sel],
                    timeout=60,
                )
                if ret.returncode != 0:
                    return None
                p = Path(tmp_sel)
                if (
                    not p.exists()
                    or p.stat().st_size == 0
                ):
                    return None
                sel = cv2.imread(tmp_sel)
                full = cv2.imread(tmp_full)
                if sel is None or full is None:
                    return None
                sh, sw = sel.shape[:2]
                scale = 1
                if full.shape[1] > mon_w * 1.5:
                    scale = 2
                res = cv2.matchTemplate(
                    full, sel, cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, max_loc = (
                    cv2.minMaxLoc(res)
                )
                if max_val > 0.7:
                    mx, my = max_loc
                    return (
                        mx // scale,
                        my // scale,
                        sw // scale,
                        sh // scale,
                    )
                return (
                    0, 0, sw // scale, sh // scale
                )
            finally:
                Path(tmp_sel).unlink(missing_ok=True)
                Path(tmp_full).unlink(missing_ok=True)

        return await loop.run_in_executor(
            None, _select
        )

    def _add_keyword(self, input_element) -> None:
        term = input_element.value.strip()
        if term:
            self.pipeline.add_manual_keyword(term)
            input_element.value = ""
