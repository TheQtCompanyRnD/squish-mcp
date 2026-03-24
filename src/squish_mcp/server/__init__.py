"""
MCP Layer - server, tool wrappers, orchestration logic, and response construction.
"""

import argparse
import logging

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider


TOOLS_ROOT = Path(__file__).resolve().parent / "tools"

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
TRANSPORT_STDIO = "stdio"
TRANSPORT_STREAMABLE_HTTP = "streamable-http"
TRANSPORT_HTTP_ALIAS = "http"

SERVER_INSTRUCTIONS = Path(__file__).resolve().parent / "instructions.md"


def load_instructions() -> str:
    try:
        with open(SERVER_INSTRUCTIONS, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Instructions file not found: {SERVER_INSTRUCTIONS}")
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Squish MCP server")
    parser.add_argument(
        "--transport",
        choices=(TRANSPORT_STDIO, TRANSPORT_STREAMABLE_HTTP, TRANSPORT_HTTP_ALIAS),
        default=TRANSPORT_STDIO,
        help="MCP transport. Use 'stdio' for local client spawning, or HTTP for URL-based clients.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host to bind for HTTP transport (default: {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        type=int,
        help=f"Port to bind for HTTP transport (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Log level for the MCP server (default: INFO).",
    )
    return parser.parse_args(argv)


def create_mcp_server() -> FastMCP:
    return FastMCP(
        "SquishRunner-Server",
        providers=[FileSystemProvider(TOOLS_ROOT)],
        instructions=load_instructions(),
    )


def run(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    mcp = create_mcp_server()

    transport = args.transport
    if transport == TRANSPORT_HTTP_ALIAS:
        transport = TRANSPORT_STREAMABLE_HTTP

    if transport == TRANSPORT_STDIO:
        mcp.run(transport=TRANSPORT_STDIO, log_level=args.log_level)
        return

    mcp.run(
        transport=TRANSPORT_STREAMABLE_HTTP,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
