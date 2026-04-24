import argparse
import logging
import sys

from sasayaki.config import Config


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("sasayaki")

    parser = argparse.ArgumentParser(
        description="ささやき女将 — AI Meeting Assistant"
    )
    parser.add_argument(
        "--mode",
        choices=["nicegui", "api"],
        default="nicegui",
        help=(
            "nicegui: legacy browser UI on localhost:7860. "
            "api: FastAPI server for the Tauri frontend."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    config = Config()
    logger.info("ささやき女将 starting (mode=%s)", args.mode)
    logger.info("System audio device: %s", config.system_audio_device)
    logger.info("Mic device: %s", config.mic_device or "(system default)")
    logger.info("Whisper model: %s", config.whisper_model)
    logger.info("Ollama model: %s", config.ollama_model)

    if args.mode == "api":
        import uvicorn

        from sasayaki.api.server import create_app

        uvicorn.run(
            create_app(config),
            host=args.host,
            port=args.port or 7861,
            log_level="info",
        )
        return

    from sasayaki.ui.app import NiceGuiApp

    app = NiceGuiApp(config)
    app.build()
    app.launch()


if __name__ == "__main__":
    main()
