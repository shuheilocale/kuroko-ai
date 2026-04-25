import argparse
import logging
import os
import sys

import uvicorn

from sasayaki.api.server import create_app
from sasayaki.config import Config


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("sasayaki")

    parser = argparse.ArgumentParser(
        description="ささやき女将 — AI Meeting Assistant API server"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("SASAYAKI_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SASAYAKI_PORT", "7861")),
    )
    args = parser.parse_args()

    config = Config()
    logger.info("ささやき女将 starting on %s:%d", args.host, args.port)
    logger.info("System audio device: %s", config.system_audio_device)
    logger.info("Mic device: %s", config.mic_device or "(system default)")
    logger.info("Whisper model: %s", config.whisper_model)
    logger.info("LLM backend: %s", config.llm_backend)

    uvicorn.run(
        create_app(config),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
