# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server that exposes Monarch Money personal finance
data to Claude Desktop and Claude Code. Built on the `monarchmoneycommunity`
Python library and the `mcp[cli]` FastMCP framework.

## Commands

```bash
# Install dependencies (add --extra dev for the test/lint toolchain)
uv sync --extra dev

# Run tests
uv run python -m pytest

# Run a single test
uv run python -m pytest tests/test_accounts.py::TestGetAccounts

# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Type check
uv run mypy src/

# Run the server directly
uv run python -m monarch_mcp_server.app

# Interactive login (one-time auth setup)
uv run python login_setup.py
```

## Architecture

The server is organized as a package, not a single file:

- **`src/monarch_mcp_server/app.py`** — Owns the global `FastMCP` instance
  (`mcp`) and the `main()` entry point. Importing `monarch_mcp_server.tools`
  here triggers tool registration as a side effect. Also defines
  `READ_ONLY_MODE` and the `write_tool()` decorator (see below).
- **`src/monarch_mcp_server/tools/*.py`** — One module per domain
  (`transactions`, `categories`, `tags`, `rules`, `splits`, `merchants`,
  `accounts`, `budgets`, `financial`, `summaries`, `auth`). Each module does
  `from monarch_mcp_server.app import mcp` and registers tools with
  `@mcp.tool()`. Mutating tools use `@write_tool()` instead.
- **`src/monarch_mcp_server/client.py`** — `get_monarch_client()` builds an
  authenticated Monarch API client.
- **`src/monarch_mcp_server/auth.py`** — Authentication helpers.
- **`src/monarch_mcp_server/secure_session.py`** — Token storage. Uses the
  system keyring when available, falls back to `~/.monarch-mcp-server/token`
  (mode 600). Exposes a global `secure_session` singleton.
- **`src/monarch_mcp_server/helpers.py`** — Reusable formatting/parsing helpers.
- **`login_setup.py`** — Standalone interactive CLI for authenticating with
  Monarch Money (email/password + MFA, or browser token paste).

## Key Patterns

- **Read-only mode**: Set `MONARCH_MCP_READ_ONLY=1` (also accepts
  `true`/`yes`/`on`) to make the server strictly read-only. The `write_tool()`
  decorator in `app.py` registers a tool normally when the flag is off, and
  becomes a no-op decorator when it is on — so mutating tools are never
  registered and are invisible to clients. Read tools stay on `@mcp.tool()`.
  When adding a **new** mutating tool (anything that creates, updates, deletes,
  uploads, sets, or triggers an institution refresh), decorate it with
  `@write_tool()` and import `write_tool` alongside `mcp`. The 21 currently
  gated writers are enumerated in `tests/test_read_only_mode.py`.
- **Tool structure**: Tools are `async def` functions that catch exceptions and
  return strings (usually JSON) rather than raising — the MCP protocol expects
  string responses.
- **Test mocking**: `tests/conftest.py` stubs the `monarchmoney` module before
  import and provides a `mock_monarch_client` fixture. Tests call the tool
  functions directly (not through MCP transport). Accept `mock_monarch_client`
  to override default responses.

## Dependencies

- `monarchmoneycommunity` — Community fork of the Monarch Money API client
- `mcp[cli]` — FastMCP server framework
- `keyring` — System keyring access for token storage
- `pydantic` — Config models
- Python 3.12–3.13 required
