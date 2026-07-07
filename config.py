"""
config.py
=========
All API security settings come from environment variables — never
hardcoded. Defaults are chosen to be SECURE BY DEFAULT: if you forget
to configure something, the system fails closed (auth required, no
open CORS), not open.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

API_KEYS: set[str] = set(filter(None, os.getenv("AI_SDDS_API_KEYS", "").split(",")))
REQUIRE_API_KEY: bool = os.getenv("AI_SDDS_REQUIRE_API_KEY", "true").lower() != "false"

# CORS origins never include a path — a browser's Origin header is
# always scheme://host[:port] only. Default is empty (deny all
# cross-origin) — fail closed, not open.
ALLOWED_ORIGINS: list[str] = [o for o in os.getenv("AI_SDDS_ALLOWED_ORIGINS", "").split(",") if o]

RATE_LIMIT: str = os.getenv("AI_SDDS_RATE_LIMIT", "30/minute")

# Small buffer added to the hard file-size cap to account for multipart
# boundary/header overhead when checking the raw Content-Length header.
UPLOAD_OVERHEAD_BYTES = 4096
