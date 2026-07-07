"""
auth.py
=======
API key check. Deliberately simple (a shared-secret header) for an
internal/SDK-style integration. For a public-facing deployment, swap
this dependency for OAuth2/JWT — the rest of the API does not care how
`verify_api_key` decides, only that it raises on failure.
"""

from __future__ import annotations
from fastapi import Header, HTTPException, status

import config


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not config.REQUIRE_API_KEY:
        return
    if not x_api_key or x_api_key not in config.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="अमान्य या अनुपस्थित API key (X-API-Key header चाहिए)",
        )
