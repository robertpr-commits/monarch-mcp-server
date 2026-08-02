"""Cached MonarchMoney client factory."""

import os
import logging
from typing import Optional

from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import MonarchMoneyEndpoints

from monarch_mcp_server.secure_session import secure_session

logger = logging.getLogger(__name__)

# Patch MonarchMoney to use new API domain
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"

# Module-level client cache
_cached_client: Optional[MonarchMoney] = None


def clear_client_cache() -> None:
    """Clear the cached client. Call after re-authentication."""
    global _cached_client
    _cached_client = None
    logger.info("Client cache cleared")


async def get_monarch_client() -> MonarchMoney:
    """Get or create a cached MonarchMoney client using secure session storage."""
    global _cached_client

    if _cached_client is not None:
        return _cached_client

    # Try a stored token: $MONARCH_TOKEN, then keyring, then file fallback
    client = secure_session.get_authenticated_client()

    if client is not None:
        logger.info(f"Using authenticated client from {secure_session.token_source()}")
        _cached_client = client
        return client

    # If no secure session, try environment credentials
    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")

    if email and password:
        try:
            client = MonarchMoney()
            await client.login(email, password)
            logger.info(
                "Successfully logged into Monarch Money with environment credentials"
            )
            # Save the session securely
            secure_session.save_authenticated_session(client)
            _cached_client = client
            return client
        except Exception as e:
            logger.error(f"Failed to login to Monarch Money: {e}")
            raise

    raise RuntimeError(
        "Authentication needed! Set MONARCH_TOKEN (a session token, works in "
        "headless environments and with MFA/SSO accounts) or MONARCH_EMAIL and "
        "MONARCH_PASSWORD in the environment, or run: python login_setup.py"
    )
