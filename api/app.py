"""
api/app.py
==========
Public HTTP surface for the Core Detection Engine. This is what a
Browser Extension, Mobile App, or third-party SDK consumer would call.

Security layers applied here, in the order a request passes through
them:
  1. limit_upload_size middleware  -> reject oversized uploads via the
                                       Content-Length header, before a
                                       single byte of the body is read.
  2. CORSMiddleware                -> only configured origins may call
                                       this API from a browser at all.
  3. verify_api_key dependency     -> shared-secret auth.
  4. @limiter.limit                -> per-client rate limiting.
  5. core.security.validate_file   -> (inside detector.scan) MIME/size
                                       re-check on the actual bytes.
  6. generic_exception_handler     -> any unexpected error returns a
                                       generic message, never a stack
                                       trace, to the caller.
"""

from __future__ import annotations
import secrets
import logging
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import config

from api.auth import verify_api_key
from api import metrics

import cv2

print("CV2 FILE:", cv2.__file__)
print("CV2 VERSION:", cv2.__version__)
print("HAS CASCADE:", hasattr(cv2, "CascadeClassifier"))
from core import detector, security

logger = logging.getLogger("ai_sdds.api")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.REQUIRE_API_KEY and not config.API_KEYS:
        generated = secrets.token_urlsafe(32)
        config.API_KEYS.add(generated)
        logger.warning(
            "कोई AI_SDDS_API_KEYS सेट नहीं थी — एक अस्थायी key बनाई गई (restart पर बदल जाएगी): %s",
            generated,
        )
    yield


app = FastAPI(
    title="AI-SDDS Core API",
    description="संवेदनशील दस्तावेज़ पहचान सेवा — आधार/PAN/IFSC/कार्ड/पासवर्ड पहचान",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-sdds-production.up.railway.app","https://ai-sdds-production.up.railway.app/v1/health"],   # empty by default = no cross-origin allowed
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type", "Accept"],
)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        cap = security.MAX_FILE_SIZE_BYTES + config.UPLOAD_OVERHEAD_BYTES
        if content_length and int(content_length) > cap:
            return JSONResponse(
                status_code=413,
                content={"detail": "फ़ाइल आकार सीमा से अधिक (अधिकतम 15MB)"},
            )
    return await call_next(request)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "अंदरूनी त्रुटि - कृपया बाद में पुनः प्रयास करें"})


@app.get("/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/metrics")
async def metrics_endpoint():
    """Prometheus scrape target. Aggregate counters only — no file
    content, no filenames, no IPs. NOTE for production deployments:
    restrict this route at the reverse-proxy/network level to internal
    scrapers only; it is intentionally left unauthenticated here only
    because that's standard Prometheus practice (the proxy/firewall is
    the real boundary, not an API key) — see SECURITY_CHECKLIST.md."""
    body, content_type = metrics.render_latest()
    return Response(content=body, media_type=content_type)


@app.post("/v1/scan", dependencies=[Depends(verify_api_key)])
@limiter.limit(config.RATE_LIMIT)
async def scan_document(
    request: Request,
    file: UploadFile = File(...)
):
    start = time.monotonic()
    file_bytes = await file.read()
    result = detector.scan(file_bytes, filename=file.filename or "upload")
    duration = time.monotonic() - start
    metrics.record_scan(result.verdict, duration)
    return JSONResponse(content=result.to_dict())




