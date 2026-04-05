import asyncio
import logging
import threading
from itertools import groupby

from nicegui import ui

from sasayaki.audio.capture import list_input_devices
from sasayaki.config import Config
from sasayaki.pipeline.orchestrator import Pipeline

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

                def on_apply():
                    self.config.system_audio_device = system_select.value
                    self.config.mic_device = mic_select.value
                    self._restart_pipeline()
                    ui.notify("デバイスを変更しました。再起動中...", type="info")

                ui.button("適用", on_click=on_apply).props("dense")
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

            # Suggestions: collapsible below the grid
            with ui.expansion("応答候補").classes("w-full"):
                suggestions_container = ui.column().classes("w-full")

            # Timer-based update via WebSocket push
            def poll():
                state = self.pipeline.get_state()

                # Transcripts
                transcript_container.clear()
                with transcript_container:
                    for t in state.transcripts:
                        css = "chat-msg chat-mic" if t.source == "mic" else "chat-msg chat-system"
                        if t.is_partial:
                            css += " chat-partial"
                        with ui.row().classes(
                            "w-full justify-end" if t.source == "mic" else "w-full justify-start"
                        ):
                            ui.label(t.text).classes(css)

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
                            ui.label("応答候補を生成中").classes(
                                "text-sm loading-dots"
                            )
                        if state.suggestions:
                            ui.markdown("\n\n".join(
                                f"**{i+1}.** {s}"
                                for i, s in enumerate(state.suggestions)
                            )).classes("opacity-50")
                    elif state.suggestions:
                        ui.markdown("\n\n".join(
                            f"**{i+1}.** {s}"
                            for i, s in enumerate(state.suggestions)
                        ))
                    else:
                        ui.label("相手の発話を待っています...").classes(
                            "text-gray-400 italic"
                        )

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

    def _add_keyword(self, input_element) -> None:
        term = input_element.value.strip()
        if term:
            self.pipeline.add_manual_keyword(term)
            input_element.value = ""
