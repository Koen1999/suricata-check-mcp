"""Entry point for running the suricata-check MCP server directly."""

from __future__ import annotations

import argparse
import logging
import sys

import suricata_check

from suricata_check_mcp._suricata_check_mcp import DEFAULT_INCLUDE, mcp


def main() -> None:
    """Instantiates and runs the FastMCP server exposing suricata-check tools.

    By default, the server runs on the stdio transport. Use ``--transport`` to select an
    alternative transport, optionally additionally pass ``--host`` and ``--port``.
    """
    parser = argparse.ArgumentParser(
        prog="suricata-check-mcp",
        description="MCP server exposing suricata-check rule analysis tools.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse", "streamable-http"),
        default="stdio",
        help="Transport protocol to use. (default: %(default)s)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to when using an HTTP-based transport. (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to when using an HTTP-based transport. (default: %(default)s)",
    )
    args = parser.parse_args()

    # An MCP stdio server must never write anything but protocol messages to stdout;
    # configure logging explicitly to stream to stderr instead.
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    # Discover and import all suricata-check extensions on the main thread before the server
    # starts. Otherwise, they are imported lazily on the first tool call inside a worker thread,
    # where importing native extension modules (e.g., numpy via xgboost) can deadlock on Windows.
    suricata_check.get_checkers(include=DEFAULT_INCLUDE, exclude=())

    if args.transport == "stdio":
        mcp.run("stdio")
    else:
        mcp.run(args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
