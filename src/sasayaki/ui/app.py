import logging

import gradio as gr

from sasayaki.pipeline.orchestrator import Pipeline

logger = logging.getLogger(__name__)

CSS = """
.transcript-box { min-height: 400px; }
.keyword-box { min-height: 400px; }
.suggestion-box { min-height: 400px; }
"""


class GradioApp:
    """3-column Gradio UI for the meeting assistant."""

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def build(self) -> gr.Blocks:
        with gr.Blocks(
            title="ささやき女将 - AI Meeting Assistant",
        ) as app:
            gr.Markdown("# 🏮 ささやき女将 — AI Meeting Assistant")

            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### 📝 文字起こし")
                    chatbot = gr.Chatbot(
                        label="会話",
                        height=500,
                        elem_classes="transcript-box",
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### 📚 キーワード")
                    keywords = gr.Dataframe(
                        headers=["用語", "説明"],
                        datatype=["str", "str"],
                        max_height=500,
                        elem_classes="keyword-box",
                        interactive=False,
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### 💡 応答候補")
                    suggestions = gr.Markdown(
                        value="*相手の発話を待っています...*",
                        elem_classes="suggestion-box",
                    )

            with gr.Row():
                status = gr.Markdown("**Status:** 起動中...")

            # Timer-based polling
            timer = gr.Timer(value=self.pipeline.config.ui_poll_interval_sec)
            timer.tick(
                fn=self._poll,
                outputs=[chatbot, keywords, suggestions, status],
            )

        self._css = CSS
        self._theme = gr.themes.Soft(primary_hue="blue")
        return app

    def launch(self, app: gr.Blocks):
        app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            css=self._css,
            theme=self._theme,
        )

    def _poll(self):
        state = self.pipeline.get_state()

        # Transcripts -> Chatbot messages
        messages = []
        for t in state.transcripts:
            role = "user" if t.source == "mic" else "assistant"
            text = t.text
            if t.is_partial:
                text = f"*{text}*"  # Italic for partial
            messages.append({"role": role, "content": text})

        # Entities -> Dataframe
        entity_data = [[e.term, e.definition] for e in state.entities]

        # Suggestions -> Markdown
        if state.suggestions:
            suggestion_md = "\n\n".join(
                f"**{i+1}.** {s}" for i, s in enumerate(state.suggestions)
            )
        else:
            suggestion_md = "*相手の発話を待っています...*"

        # Status
        if state.error:
            status_md = f"**Status:** ⚠️ エラー: {state.error}"
        elif state.is_running:
            ollama_status = "✅" if state.ollama_ok else "❌"
            status_md = (
                f"**Status:** 🎙️ 録音中... | "
                f"**System:** {state.system_device} | "
                f"**Mic:** {state.mic_device} | "
                f"**Ollama:** {ollama_status} | "
                f"発話: {len(state.transcripts)}件, キーワード: {len(state.entities)}件"
            )
        else:
            status_md = "**Status:** ⏹ 停止中"

        return messages, entity_data, suggestion_md, status_md
