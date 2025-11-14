# config.py
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# ============================
# TELEGRAM BOT SETTINGS
# ============================
# Use env BOT_TOKEN if available; fallback to hardcoded token only if set here.
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8512342341:AAE5CR9a3Jd8ZVauqRARWPWMqniiGp_Gfw4"
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in .env or config")

# ============================
# ADMIN SETTINGS
# ============================
# ADMIN_TG_ID may be provided as env var; fallback to local value if necessary
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "7955075357"))

# older code expects ADMIN_IDS list; ensure it's a list of ints
ADMIN_IDS = [ADMIN_TG_ID] if ADMIN_TG_ID else []


# ============================
# DATABASE
# ============================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///referral.db")


# ============================
# REDIS (used for WebApp sessions)
# ============================
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")


# ============================
# WEBAPP URL (Telegram mini app)
# ============================
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://127.0.0.1:8000").rstrip("/")


# ============================================================
#  DEPOSIT SYSTEM CONFIG
# ============================================================

# Minimum first-time deposit (USD)
MIN_FIRST_DEPOSIT = 20   # $20

# Subsequent deposits must be multiples of this (USD)
SUBSEQUENT_MULTIPLE = 10

# Deposit split
MUSD_SPLIT = 0.70
MSTC_SPLIT = 0.30


# ============================================================
#  EARNING / CAP CONFIG
# ============================================================

# User can earn up to N x their total deposit
EARNING_CAP_MULTIPLIER = 3

# After reaching cap, user has this many hours to reactivate
GRACE_HOURS = 24


# ============================================================
#  RANKING SYSTEM CONFIG
# ============================================================

class Rank:
    ORIGIN = "Origin"
    LIFE_CHANGER = "Life Changer"
    ADVISOR = "Advisor"
    VISIONARY = "Visionary"
    CREATOR = "Creator"

# REQUIREMENTS structure (keeps previous semantics)
REQUIREMENTS = {
    Rank.ORIGIN: {
        "team_business": 0,
        "active_origin": 0,
        "monthly_club": 0,
        "club_turnover_percent": 0,
        "reward_percent": 5
    },
    Rank.LIFE_CHANGER: {
        "team_business": 1000,
        "active_origin": 10,
        "monthly_club": 300,
        "club_turnover_percent": 2,
        "reward_percent": 10
    },
    Rank.ADVISOR: {
        "team_business": 5000,
        "active_origin": 0,
        "monthly_club": 1500,
        "club_turnover_percent": 2,
        "reward_percent": 15
    },
    Rank.VISIONARY: {
        "team_business": 25000,
        "active_origin": 0,
        "monthly_club": 7500,
        "club_turnover_percent": 2,
        "reward_percent": 20
    },
    Rank.CREATOR: {
        "team_business": 100000,
        "active_origin": 0,
        "monthly_club": 30000,
        "club_turnover_percent": 2,
        "reward_percent": 25
    },
}

# RANK_REWARD_PCT expected by reward_service: map Rank.* -> decimal fraction
RANK_REWARD_PCT = {
    Rank.ORIGIN: 0.05,       # 5%
    Rank.LIFE_CHANGER: 0.10, # 10%
    Rank.ADVISOR: 0.15,      # 15%
    Rank.VISIONARY: 0.20,    # 20%
    Rank.CREATOR: 0.25       # 25%
}


# ============================
# DEBUG SUMMARY
# ============================
print("===== CONFIG LOADED =====")
print("BOT_TOKEN:", "OK" if BOT_TOKEN else "MISSING")
print("DATABASE_URL:", DATABASE_URL)
print("REDIS_URL:", REDIS_URL)
print("WEBAPP_URL:", WEBAPP_URL)
print("ADMIN_IDS:", ADMIN_IDS)
print("Deposit Rules: Min=${}, Multiple=${}, Split={}/{}".format(
    MIN_FIRST_DEPOSIT, SUBSEQUENT_MULTIPLE, int(MUSD_SPLIT*100), int(MSTC_SPLIT*100)
))
print("Rank System Loaded, RANK_REWARD_PCT OK")
print("==========================")
