from __future__ import annotations

from chassis_auth.models import TokenPair, UserInfo
from chassis_auth.protocols import AuthProvider


class DemoOAuthProvider:
    """Fake OAuth provider for demonstration purposes.

    Simulates a complete OAuth 2.0 flow without external dependencies.
    Accepts any authorization code and returns a demo user.

    Implements the ``AuthProvider`` Protocol via structural subtyping.
    """

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        return f"{redirect_uri}?code=demo_code&state={state}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenPair:
        return TokenPair(
            access_token="demo_access_token",
            refresh_token="demo_refresh_token",
            expires_in=3600,
        )

    async def refresh_token(self, refresh_token: str) -> TokenPair | None:
        return None

    async def get_user_info(self, access_token: str) -> UserInfo:
        return UserInfo(
            provider_id="demo_user",
            name="Demo User",
            email="demo@example.com",
        )
