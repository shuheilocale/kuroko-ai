import asyncio
import logging
import subprocess
import tempfile
import threading
from datetime import datetime, timezone, timedelta
from itertools import groupby
from pathlib import Path

from nicegui import ui

from sasayaki.audio.capture import list_input_devices
from sasayaki.config import Config
from sasayaki.pipeline.orchestrator import Pipeline
from sasayaki.vision.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)


class NiceGuiApp:
    """3-column NiceGUI UI for the meeting assistant."""

    def __init__(self, config: Config):
        self.config = config
        self.pipeline = Pipeline(config)
        self._pipeline_thread: threading.Thread | None = None

    def _start_pipeline(self):
        """Start the pipeline in a background daemon thread."""
        self.pipeline.reset_state()
        loop = asyncio.new_event_loop()

        def run():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.pipeline.run())

        self._pipeline_thread = threading.Thread(target=run, daemon=True)
        self._pipeline_thread.start()

    def _restart_pipeline(self):
        """Stop the running pipeline and start a new one."""
        self.pipeline.request_stop()
        if self._pipeline_thread:
            self._pipeline_thread.join(timeout=5)
        self._start_pipeline()

    def build(self) -> None:
        @ui.page("/")
        def index():
            ui.add_head_html("""
                <style>
                    .transcript-box { min-height: 400px; max-height: 500px; overflow-y: auto; }
                    .keyword-box { min-height: 400px; max-height: 500px; overflow-y: auto; }
                    .profile-box { min-height: 400px; max-height: 500px; overflow-y: auto; }
                    .profile-name { font-size: 1.3em; font-weight: bold; margin-bottom: 8px; }
                    .profile-category { font-weight: 600; color: #1565c0; margin-top: 8px; }
                    .profile-fact { padding: 2px 0 2px 12px; border-left: 2px solid #e0e0e0; margin: 2px 0; }
                    .chat-msg { padding: 6px 12px; border-radius: 12px; margin: 2px 0; max-width: 85%; }
                    .chat-mic { background: #e3f2fd; align-self: flex-end; }
                    .chat-system { background: #f3e5f5; align-self: flex-start; }
                    .chat-partial { font-style: italic; opacity: 0.7; }
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.4; }
                    }
                    .loading-pulse { animation: pulse 1.5s ease-in-out infinite; color: #888; }
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
                </style>
            """)

            # Header
            ui.label("ささやき女将 — AI Meeting Assistant").classes(
                "text-2xl font-bold"
            )

            # Device selectors + status
            devices = list_input_devices()
            monitors = ScreenCapture.list_monitors()
            monitor_options = {
                m["index"]: f"Monitor {m['index']} ({m['width']}x{m['height']})"
                for m in monitors
            }

            with ui.row().classes("w-full items-center gap-4"):
                system_select = ui.select(
                    devices,
                    value=self.config.system_audio_device,
                    label="System Audio",
                ).classes("w-48")
                mic_select = ui.select(
                    devices,
                    value=self.config.mic_device,
                    label="Mic",
                ).classes("w-48")
                monitor_select = ui.select(
                    monitor_options,
                    value=1,
                    label="Screen Capture",
                ).classes("w-56")

                def on_apply():
                    self.config.system_audio_device = system_select.value
                    self.config.mic_device = mic_select.value
                    self.config.screen_monitor = monitor_select.value
                    self._restart_pipeline()
                    ui.notify(
                        "設定を適用しました。再起動中...",
                        type="info",
                    )

                ui.button("適用", on_click=on_apply).props("dense")

            with ui.row().classes("w-full items-center gap-2"):
                region_label = ui.label(
                    "キャプチャ範囲: 全画面"
                ).classes("text-sm")

                async def select_region():
                    region_label.set_text(
                        "キャプチャ範囲: 選択中..."
                    )
                    result = await self._select_screen_region()
                    if result:
                        x, y, w, h = result
                        if self.pipeline._screen_capture:
                            self.pipeline._screen_capture.region = (
                                x, y, w, h
                            )
                        region_label.set_text(
                            f"キャプチャ範囲: "
                            f"{w}x{h} ({x},{y})"
                        )
                        ui.notify(
                            f"範囲設定: {w}x{h}",
                            type="positive",
                        )
                    else:
                        region_label.set_text(
                            "キャプチャ範囲: 全画面"
                        )
                        ui.notify(
                            "範囲選択がキャンセルされました",
                            type="warning",
                        )

                ui.button(
                    "範囲選択", on_click=select_region
                ).props("dense")

                def reset_region():
                    if self.pipeline._screen_capture:
                        self.pipeline._screen_capture.region = (
                            0, 0, 0, 0
                        )
                    region_label.set_text(
                        "キャプチャ範囲: 全画面"
                    )
                    ui.notify("全画面に戻しました", type="info")

                ui.button(
                    "全画面に戻す", on_click=reset_region
                ).props("dense flat")

            with ui.row().classes("w-full items-center gap-4"):
                ui.label("System:").classes("text-sm w-16")
                system_level_bar = ui.linear_progress(
                    value=0, show_value=False
                ).props("color=purple").classes("w-48")
                ui.label("Mic:").classes("text-sm w-10")
                mic_level_bar = ui.linear_progress(
                    value=0, show_value=False
                ).props("color=blue").classes("w-48")
                status_label = ui.markdown("**Status:** 起動中...")

            # 3-column layout
            with ui.grid(columns="2fr 1fr 1fr").classes("w-full gap-4"):
                # Left: Transcript
                with ui.card().classes("w-full"):
                    ui.label("文字起こし").classes("text-lg font-semibold")
                    transcript_container = ui.column().classes(
                        "transcript-box w-full"
                    )

                # Middle: Keywords
                with ui.card().classes("w-full"):
                    ui.label("キーワード").classes("text-lg font-semibold")
                    with ui.row().classes("w-full items-center"):
                        keyword_input = ui.input(
                            placeholder="用語を入力して調べる..."
                        ).classes("flex-grow")
                        ui.button(
                            "検索",
                            on_click=lambda: self._add_keyword(keyword_input),
                        ).props("dense")
                    keyword_input.on(
                        "keydown.enter",
                        lambda: self._add_keyword(keyword_input),
                    )
                    keywords_container = ui.column().classes(
                        "keyword-box w-full"
                    )

                # Right: Profile
                with ui.card().classes("w-full"):
                    ui.label("相手のプロフィール").classes("text-lg font-semibold")
                    profile_container = ui.column().classes(
                        "profile-box w-full"
                    )

            # Face analysis
            with ui.card().classes("w-full"):
                ui.label("表情分析").classes("text-lg font-semibold")
                with ui.row().classes("w-full gap-8 items-start"):
                    # Emotion meters
                    with ui.column().classes("gap-1"):
                        EMOTION_LABELS = {
                            "joy": ("喜び", "amber"),
                            "surprise": ("驚き", "cyan"),
                            "concern": ("困惑", "red"),
                            "neutral": ("平常", "grey"),
                        }
                        emotion_bars = {}
                        for key, (label, color) in EMOTION_LABELS.items():
                            with ui.row().classes("items-center gap-2"):
                                ui.label(label).classes("text-sm w-10")
                                bar = ui.linear_progress(
                                    value=0, show_value=False
                                ).props(
                                    f"color={color}"
                                ).classes("w-32")
                                emotion_bars[key] = bar
                    # Face thumbnail + status
                    with ui.column().classes("gap-2 items-center"):
                        face_image_html = ui.html(
                            '<div style="width:96px;height:96px;'
                            'background:#eee;border-radius:8px">'
                            '</div>'
                        )
                        face_status_label = ui.label(
                            "顔未検出"
                        ).classes("text-sm text-gray-400")
                        nod_label = ui.label(
                            "うなずき: 0回"
                        ).classes("text-sm")
                        fps_label = ui.label(
                            "FPS: --"
                        ).classes("text-xs text-gray-400")
                    # Expression change log
                    with ui.column().classes("flex-grow"):
                        ui.label("表情変化ログ").classes(
                            "text-sm font-semibold"
                        )
                        expression_log = ui.column().classes(
                            "max-h-24 overflow-y-auto"
                        )

            # Suggestions: always visible below the grid
            with ui.card().classes("w-full"):
                ui.label("応答候補").classes("text-lg font-semibold")
                with ui.row().classes("w-full flex-wrap gap-2"):
                    style_buttons = {
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
                    }
                    for style, color in style_buttons.items():
                        ui.button(
                            style,
                            on_click=lambda s=style: self.pipeline.request_suggestions(s),
                        ).props(f"color={color}")
                suggestions_container = ui.column().classes("w-full")

            # Timer-based update via WebSocket push
            jst = timezone(timedelta(hours=9))

            def poll():
                state = self.pipeline.get_state()

                # Transcripts
                transcript_container.clear()
                with transcript_container:
                    for t in state.transcripts:
                        css = "chat-msg chat-mic" if t.source == "mic" else "chat-msg chat-system"
                        if t.is_partial:
                            css += " chat-partial"
                        ts = datetime.fromtimestamp(
                            t.timestamp, tz=jst
                        ).strftime("%H:%M:%S")
                        with ui.row().classes(
                            "w-full items-center justify-end gap-2"
                            if t.source == "mic"
                            else "w-full items-center justify-start gap-2"
                        ):
                            if t.source != "mic":
                                ui.label(ts).classes(
                                    "text-xs text-gray-400"
                                )
                            ui.label(t.text).classes(css)
                            if t.source == "mic":
                                ui.label(ts).classes(
                                    "text-xs text-gray-400"
                                )

                # Entities
                if state.entities:
                    keywords_container.clear()
                    with keywords_container:
                        for e in state.entities:
                            if e.loading:
                                with ui.row().classes("items-center gap-2 loading-pulse"):
                                    ui.spinner(size="sm")
                                    ui.label(e.term).classes("font-bold")
                                    ui.label("検索中").classes("text-sm loading-dots")
                            else:
                                ui.markdown(
                                    f"**{e.term}**\n{e.definition}"
                                )
                                ui.separator()
                else:
                    keywords_container.clear()
                    with keywords_container:
                        ui.label("キーワードを検出中...").classes(
                            "text-gray-400 italic"
                        )

                # Profile
                profile_container.clear()
                with profile_container:
                    profile = state.profile
                    if profile.name:
                        ui.label(profile.name).classes("profile-name")
                    if profile.summary:
                        ui.label(profile.summary).classes(
                            "text-sm text-gray-600 italic"
                        )
                        ui.separator()
                    if profile.facts:
                        sorted_facts = sorted(
                            profile.facts, key=lambda f: f.category
                        )
                        for category, group in groupby(
                            sorted_facts, key=lambda f: f.category
                        ):
                            ui.label(category).classes("profile-category")
                            for fact in group:
                                ui.label(f"  {fact.content}").classes(
                                    "profile-fact"
                                )
                    elif state.profiling:
                        with ui.row().classes(
                            "items-center gap-2 loading-pulse"
                        ):
                            ui.spinner(size="sm")
                            ui.label("プロフィールを分析中").classes(
                                "text-sm loading-dots"
                            )
                    else:
                        ui.label("会話からプロフィールを構築中...").classes(
                            "text-gray-400 italic"
                        )

                # Suggestions
                suggestions_container.clear()
                with suggestions_container:
                    if state.suggesting:
                        with ui.row().classes("items-center gap-2 loading-pulse"):
                            ui.spinner(size="sm")
                            ui.label(
                                f"「{state.suggestion_style}」で応答候補を生成中"
                            ).classes("text-sm loading-dots")
                        if state.suggestions:
                            ui.markdown("\n\n".join(
                                f"**{i+1}.** {s}"
                                for i, s in enumerate(state.suggestions)
                            )).classes("opacity-50")
                    elif state.suggestions:
                        if state.suggestion_style:
                            ui.label(
                                f"スタイル: {state.suggestion_style}"
                            ).classes("text-sm text-gray-500")
                        ui.markdown("\n\n".join(
                            f"**{i+1}.** {s}"
                            for i, s in enumerate(state.suggestions)
                        ))
                    else:
                        ui.label(
                            "スタイルを選んでボタンを押してください"
                        ).classes("text-gray-400 italic")

                # Audio levels
                system_level_bar.set_value(state.system_level)
                mic_level_bar.set_value(state.mic_level)

                # Face analysis
                face = state.face
                emotion_bars["joy"].set_value(face.joy)
                emotion_bars["surprise"].set_value(face.surprise)
                emotion_bars["concern"].set_value(face.concern)
                emotion_bars["neutral"].set_value(face.neutral)
                fps_label.set_text(f"FPS: {face.fps:.1f}")
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
                        f"検出中 — {dominant}"
                    )
                    face_status_label.classes(
                        remove="text-gray-400",
                        add="text-green-600",
                    )
                    if face.face_image_base64:
                        face_image_html.set_content(
                            f'<img src="data:image/jpeg;base64,'
                            f'{face.face_image_base64}" '
                            f'style="width:96px;height:96px;'
                            f'object-fit:cover;border-radius:8px">'
                        )
                else:
                    face_status_label.set_text("顔未検出")
                    face_status_label.classes(
                        remove="text-green-600",
                        add="text-gray-400",
                    )
                    face_image_html.set_content(
                        '<div style="width:96px;height:96px;'
                        'background:#eee;border-radius:8px">'
                        '</div>'
                    )
                nod_label.set_text(f"うなずき: {face.nod_count}回")
                expression_log.clear()
                with expression_log:
                    for evt in reversed(
                        face.expression_changes[-10:]
                    ):
                        ts = datetime.fromtimestamp(
                            evt.timestamp, tz=jst
                        ).strftime("%H:%M:%S")
                        ui.label(
                            f"{ts} {evt.detail}"
                            + (f" ({evt.transcript_snippet}...)"
                               if evt.transcript_snippet else "")
                        ).classes("text-xs")

                # Status
                if state.error:
                    status_label.set_content(
                        f"**Status:** エラー: {state.error}"
                    )
                elif state.is_running:
                    ollama_status = "OK" if state.ollama_ok else "NG"
                    status_label.set_content(
                        f"**Status:** 録音中... | "
                        f"**Ollama:** {ollama_status} | "
                        f"発話: {len(state.transcripts)}件, "
                        f"キーワード: {len(state.entities)}件, "
                        f"プロフィール: {len(state.profile.facts)}件"
                    )
                else:
                    status_label.set_content("**Status:** 停止中")

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
        """Use macOS native screenshot selection to pick a region.

        Returns (x, y, w, h) in screen coordinates, or None.
        """
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
                # 1) Capture full screen (silent, no sound)
                subprocess.run(
                    ["screencapture", "-x", tmp_full],
                    timeout=10,
                )
                # 2) Interactive region selection
                ret = subprocess.run(
                    ["screencapture", "-i", "-s", tmp_sel],
                    timeout=60,
                )
                if ret.returncode != 0:
                    return None
                p = Path(tmp_sel)
                if not p.exists() or p.stat().st_size == 0:
                    return None

                sel = cv2.imread(tmp_sel)
                full = cv2.imread(tmp_full)
                if sel is None or full is None:
                    return None

                sh, sw = sel.shape[:2]

                # Retina scale detection
                scale = 1
                if full.shape[1] > mon_w * 1.5:
                    scale = 2

                # Template match to find position
                res = cv2.matchTemplate(
                    full, sel, cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if max_val > 0.7:
                    mx, my = max_loc
                    return (
                        mx // scale,
                        my // scale,
                        sw // scale,
                        sh // scale,
                    )
                return (0, 0, sw // scale, sh // scale)
            finally:
                Path(tmp_sel).unlink(missing_ok=True)
                Path(tmp_full).unlink(missing_ok=True)

        return await loop.run_in_executor(None, _select)

    def _add_keyword(self, input_element) -> None:
        term = input_element.value.strip()
        if term:
            self.pipeline.add_manual_keyword(term)
            input_element.value = ""
