# webapp/app.py
import logging
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db.session import SessionLocal
from db.models import User, Deposit

# Telegram verification helpers (Redis-backed or in-memory)
from webapp.telegram_init_verify import (
    verify_init_data,
    create_session_for_params,
    get_session,
)

# Optional redis helpers (if using Redis version of telegram_init_verify)
try:
    from webapp.telegram_init_verify import get_redis, _session_redis_key
except Exception:
    get_redis = None
    _session_redis_key = None

# Optional in-memory session dict (if file exports it)
try:
    from webapp.telegram_init_verify import SESSION_TOKENS
except Exception:
    SESSION_TOKENS = None

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI()

# --- FIX: Use absolute path for static directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # path to /webapp/

STATIC_DIR = os.path.join(BASE_DIR, "web_static")

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


# --------------------------------------
