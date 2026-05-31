"""FastMCP application instance and entry point."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Monarch Money MCP Server")

# Read-only mode: when MONARCH_MCP_READ_ONLY is truthy, the server refuses to
# register any mutating ("write") tool, leaving only read tools available.
READ_ONLY_MODE = os.getenv("MONARCH_MCP_READ_ONLY", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

if READ_ONLY_MODE:
    logger.info("MONARCH_MCP_READ_ONLY is set — write tools will not be registered.")


def write_tool(*args: Any, **kwargs: Any) -> Any:
    """Register a mutating tool, unless read-only mode is enabled.

    Drop-in replacement for ``@mcp.tool()`` on any tool that creates, updates,
    deletes, or otherwise changes data (or triggers an institution refresh).
    In read-only mode it returns a no-op decorator, so the function is never
    registered with FastMCP and is invisible to clients.
    """
    if READ_ONLY_MODE:

        def decorator(func: Any) -> Any:
            return func

        return decorator

    return mcp.tool(*args, **kwargs)


# Import tools package to trigger @mcp.tool() registration
import monarch_mcp_server.tools  # noqa: E402, F401

# Export for `mcp run`
app = mcp


def main() -> None:
    """Main entry point for the server."""
    logger.info("Starting Monarch Money MCP Server...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to run server: {str(e)}")
        raise


if __name__ == "__main__":
    main()
