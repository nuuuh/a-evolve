"""Entry point: ``python -m agent_evolve.algorithms.navigation.studio``."""

from __future__ import annotations

import argparse

from .server import launch


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent_evolve.algorithms.navigation.studio",
        description="Visual studio for designing evolution systems.",
    )
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    args = parser.parse_args()

    launch(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
