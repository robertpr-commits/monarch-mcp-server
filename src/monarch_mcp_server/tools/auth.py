"""Authentication tools."""

import logging
import os

from mcp.server.fastmcp import Context

from monarch_mcp_server import auth
from monarch_mcp_server.app import mcp
from monarch_mcp_server.secure_session import TOKEN_ENV_VAR, secure_session

logger = logging.getLogger(__name__)


@mcp.tool()
async def setup_authentication() -> str:
    """Get instructions for setting up secure authentication with Monarch Money."""
    return """🔐 Monarch Money - Authentication Options

Option 1: Elicitation login (Recommended for interactive clients)
   Call 'monarch_login' to enter email/password (and MFA if needed)
   via a secure form in your client UI. Credentials never pass
   through the model. Or 'monarch_login_with_token' to paste a
   browser-copied session token.

Option 2: Email/Password (Terminal)
   Run in terminal: python login_setup.py

Option 3: MONARCH_TOKEN environment variable (Headless / containers)
   Set MONARCH_TOKEN to a session token copied from browser DevTools →
   Application → Local Storage → app.monarchmoney.com, key 'token'.
   Use this where no interactive login is possible — Docker, CI, or
   Claude Code on the web. It also works for MFA and SSO accounts,
   which cannot authenticate via MONARCH_EMAIL/MONARCH_PASSWORD.
   Set it as a secret in your environment config, never in source.

Call 'monarch_logout' to clear the stored session.

✅ Session persists across restarts
✅ Token stored securely in system keyring
ℹ️  MONARCH_TOKEN takes precedence over any stored token"""


@mcp.tool()
async def monarch_login(ctx: Context) -> str:
    """Sign in to Monarch Money.

    Opens a secure form in the client UI to collect email, password, and
    (if required) an MFA code. Credentials never pass through the model —
    they flow client-UI → server directly via the MCP protocol.
    """
    return await auth.login_interactive(ctx)


@mcp.tool()
async def monarch_login_with_token(ctx: Context) -> str:
    """Sign in to Monarch Money using a browser-copied session token.

    Useful for SSO users who can't use password login. Grab the token from
    browser DevTools → Application → Local Storage → app.monarchmoney.com.
    """
    return await auth.login_with_token_interactive(ctx)


@mcp.tool()
async def monarch_logout() -> str:
    """Clear the stored Monarch Money session from the system keyring."""
    return await auth.logout()


@mcp.tool()
async def check_auth_status() -> str:
    """Check if already authenticated with Monarch Money."""
    try:
        source = secure_session.token_source()
        if source:
            status = f"✅ Authentication token found (source: {source})\n"
        else:
            status = "❌ No authentication token found\n"

        if source == f"${TOKEN_ENV_VAR}":
            status += (
                "ℹ️  The environment variable takes precedence over any token "
                "stored in the keyring or file fallback.\n"
            )

        email = os.getenv("MONARCH_EMAIL")
        if email:
            status += f"📧 Environment email: {email}\n"

        status += (
            "\n💡 Try get_accounts to test connection, or call "
            "setup_authentication for sign-in options."
        )

        return status
    except Exception as e:
        return f"Error checking auth status: {str(e)}"


@mcp.tool()
async def debug_session_loading() -> str:
    """Debug session token loading issues."""
    try:
        token = secure_session.load_token()
        if token:
            return f"✅ Token found (source: {secure_session.token_source()})."
        return (
            "❌ No token found. Set MONARCH_TOKEN or run login_setup.py "
            "to authenticate."
        )
    except Exception as e:
        logger.exception("Keyring access failed")
        return f"❌ Keyring access failed: {type(e).__name__}: {e}"
