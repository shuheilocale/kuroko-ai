import argparse
import logging
import os
import sys

import uvicorn

from sasayaki.config import Config

from .server import create_app


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="sasayaki API server")
    parser.add_argument(
        "--host",
        default=os.environ.get("SASAYAKI_HOST", "127.0.0.1"),
        help="Bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SASAYAKI_PORT", "7861")),
        help="Bind port (default: 7861)",
    )
    args = parser.parse_args()

    config = Config()
    app = create_app(config)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        # No reload: we hold long-lived ML models that must not be re-imported.
    )


if __name__ == "__main__":
    main()
