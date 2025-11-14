# webapp/telegram_init_verify.py (Redis-backed)
import hashlib
import hmac
import time
import secrets
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
import redis
from config import BOT_TOKEN, REDIS_URL

logger = logging.getLogger(__name__)

# TTL for session tokens (seconds)
DEFAULT_SESSION_TTL = 15 * 60  # 15 minutes
# Replay tolerance (seconds)
AUTH_DATE_TOLERANCE_SECONDS = 24 * 60 * 60

# Initialize Redis client (connection errors will raise)
_redis: Optional[redis.Redis] = None
def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def parse_init_data(init_data: str) -> Dict[str, str]:
    if not init_data:
        raise ValueError("empty init_data")
    pairs: Dict[str, str] = {}
    for line in init_data.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        pairs[k] = v
    return pairs


def build_data_check_string(params: Dict[str, str]) -> str:
    items = [(k, v) for k, v in params.items() if k != "hash"]
    items_sorted = sorted(items, key=lambda kv: kv[0])
    return "\n".join(f"{k}={v}" for k, v in items_sorted)


def compute_hmac_hex(bot_token: str, data_check_string: str) -> str:
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    mac = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def verify_init_data(init_data: str, *, bot_token: str = BOT_TOKEN, require_recent: bool = True) -> Dict[str, str]:
    try:
        params = parse_init_data(init_data)
    except Exception as e:
        logger.debug("parse_init_data failed: %s", e)
        raise HTTPException(status_code=400, detail="Failed to parse init_data")

    provided_hash = params.get("hash")
    if not provided_hash:
        raise HTTPException(status_code=400, detail="init_data missing hash")

    data_check_string = build_data_check_string(params)
    expected_hash = compute_hmac_hex(bot_token, data_check_string)

    if not hmac.compare_digest(expected_hash, provided_hash):
        logger.warning("init_data hash mismatch. expected=%s provided=%s", expected_hash, provided_hash)
        raise HTTPException(status_code=401, detail="Invalid init_data signature")

    if require_recent:
        auth_date_str = params.get("auth_date") or params.get("authDate") or params.get("authdate")
        if not auth_date_str:
            raise HTTPException(status_code=400, detail="auth_date missing in init_data")
        try:
            auth_date = int(auth_date_str)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid auth_date in init_data")
        now = int(time.time())
        if abs(now - auth_date) > AUTH_DATE_TOLERANCE_SECONDS:
            logger.warning("init_data auth_date out of tolerance: now=%s auth_date=%s", now, auth_date)
            raise HTTPException(status_code=401, detail="init_data too old (possible replay)")

    return params


# Session token keys in Redis will be stored as: "tg_session:<token>" -> JSON-like fields as a Redis hash
def _session_redis_key(token: str) -> str:
    return f"tg_session:{token}"


def create_session_for_params(params: Dict[str, str], ttl_seconds: int = DEFAULT_SESSION_TTL) -> Dict[str, Any]:
    tg_id = params.get("id") or params.get("user_id") or params.get("userId") or params.get("tg_id")
    try:
        tg_id_int = int(tg_id)
    except Exception:
        tg_id_int = 0

    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + int(ttl_seconds)
    r = get_redis()
    key = _session_redis_key(token)
    # store minimal fields
    r.hset(key, mapping={
        "telegram_id": str(tg_id_int),
        "username": params.get("username") or params.get("user_name") or "",
        "expires_at": str(expires_at),
        "created_at": str(int(time.time()))
    })
    r.expire(key, int(ttl_seconds))
    logger.debug("created redis session token for tg_id=%s token=%s expires_at=%s", tg_id_int, token, expires_at)
    return {"token": token, "telegram_id": tg_id_int, "expires_at": expires_at}


def get_session(token: str) -> Dict[str, Any]:
    r = get_redis()
    key = _session_redis_key(token)
    if not r.exists(key):
        logger.debug("redis session not found or expired: %s", token)
        raise HTTPException(status_code=401, detail="invalid or expired session token")
    data = r.hgetall(key)
    if not data:
        raise HTTPException(status_code=401, detail="invalid or expired session token")
    # refresh TTL if you want sliding sessions (optional). Here we won't refresh automatically.
    try:
        return {
            "telegram_id": int(data.get("telegram_id", "0")),
            "username": data.get("username"),
            "expires_at": int(data.get("expires_at", "0")),
            "created_at": int(data.get("created_at", "0")),
        }
    except Exception:
        raise HTTPException(status_code=401, detail="invalid session data")
