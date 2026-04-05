import logging
import sys

from sasayaki.config import Config
from sasayaki.ui.app import NiceGuiApp


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

    app = NiceGuiApp(config)
    app.build()
    app.launch()


if __name__ == "__main__":
    main()
