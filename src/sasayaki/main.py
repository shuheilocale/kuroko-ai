import asyncio
import logging
import sys
import threading

from sasayaki.config import Config
from sasayaki.pipeline.orchestrator import Pipeline
from sasayaki.ui.app import GradioApp


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("sasayaki")

    config = Config()
    logger.info("ささやき女将 starting...")
    logger.info("System audio device: %s", config.system_audio_device)
    logger.info("Mic device: %s", config.mic_device or "(system default)")
    logger.info("Whisper model: %s", config.whisper_model)
    logger.info("Ollama model: %s", config.ollama_model)

    pipeline = Pipeline(config)
    ui = GradioApp(pipeline)
    app = ui.build()

    # Run pipeline in a background daemon thread
    loop = asyncio.new_event_loop()

    def run_pipeline():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(pipeline.run())

    pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
    pipeline_thread.start()

    # Launch Gradio on main thread
    ui.launch(app)


if __name__ == "__main__":
    main()
