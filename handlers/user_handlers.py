# handlers/user_handlers.py
import logging
from urllib.parse import urlparse, parse_qs

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
)

import config
from services.user_service import get_or_create_user, set_referrer_if_first_time, current_rank, earning_cap_left

logger = logging.getLogger(__name__)


# ---------------------------
# Utility: build webapp markup
# ---------------------------
def build_webapp_markup_for_user(telegram_id: int):
    """
    Build InlineKeyboardMarkup that opens the Telegram Web App.
    Expects config.WEBAPP_URL to point at the publicly accessible
    /static/index.html path (ngrok or production).
    """
    base = config.WEBAPP_URL.rstrip("/") if getattr(config, "WEBAPP_URL", None) else ""
    if not base:
        return None

    # include ref query param for UI convenience (do not trust it server-side)
    url = f"{base}?ref={telegram_id}"
    webapp_info = WebAppInfo(url=url)
    btn = InlineKeyboardButton(text="💳 Open Deposit Web App", web_app=webapp_info)
    return InlineKeyboardMarkup([[btn]])


# ---------------------------
# /start handler
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles /start [referral_id|resume_deposit]
    If a start param is present and is a telegram id, attempt to set referrer.
    """
    tg_user = update.effective_user
    msg_text = update.message.text if update.message else ""
    args = msg_text.split()
    ref_from = None

    # Try to read deep-link start param if provided (Telegram app gives it as part of /start param)
    # Example: /start 123456789  OR /start resume_deposit
    if len(args) >= 2:
        ref_param = args[1]
        # numeric telegram id
        if ref_param.isdigit():
            try:
                ref_from = int(ref_param)
            except Exception:
                ref_from = None

    # Create or fetch user
    if tg_user:
        user = get_or_create_user(tg_user)
        # If there is a referral id, set it if user is first time
        if ref_from:
            try:
                set_referrer_if_first_time(user.id, int(ref_from))
            except Exception as e:
                logger.exception("set_referrer_if_first_time failed: %s", e)

    # Basic welcome message + WebApp button if configured
    welcome = (
        "👋 Welcome!\n\n"
        "How it works\n"
        "• Step 1: /register (auto)\n"
        "• Step 2: /deposit & wait for approval\n"
        "• Step 3: Share your /link and earn\n"
    )
    # send welcome (first message)
    if update.message:
        await update.message.reply_text(welcome)

        # Then send a WebApp button if WEBAPP_URL is configured
        if tg_user and getattr(config, "WEBAPP_URL", None):
            markup = build_webapp_markup_for_user(tg_user.id)
            if markup:
                await update.message.reply_text("Open the deposit Web App:", reply_markup=markup)
            else:
                # fallback: send plain referral link
                bot_username = getattr(config, "BOT_USERNAME", None) or context.bot.username or "bot"
                ref_link = f"https://t.me/{bot_username}?start={tg_user.id}"
                await update.message.reply_text(f"Your referral link:\n{ref_link}")
    else:
        # No message object (maybe callback), just log
        logger.info("start called with no message object")


# ---------------------------
# /register handler
# ---------------------------
async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if not tg_user:
        await update.message.reply_text("Unable to detect user.")
        return

    try:
        user = get_or_create_user(tg_user)
        await update.message.reply_text("Registration successful. You can now deposit via the Web App.")
    except Exception as e:
        logger.exception("register failed: %s", e)
        await update.message.reply_text("Registration failed. Please try again later.")


# ---------------------------
# /link handler  - sends WebApp button + fallback link
# ---------------------------
async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if not tg_user:
        await update.message.reply_text("Unable to identify user.")
        return

    # If WEBAPP_URL configured -> send WebApp button
    if getattr(config, "WEBAPP_URL", None):
        markup = build_webapp_markup_for_user(tg_user.id)
        if markup:
            await update.message.reply_text("Open your deposit & referral mini app:", reply_markup=markup)
            return

    # Fallback: plain referral link
    bot_username = getattr(config, "BOT_USERNAME", None) or context.bot.username or "bot"
    ref_link = f"https://t.me/{bot_username}?start={tg_user.id}"
    await update.message.reply_text(f"Your referral link:\n{ref_link}\n\nShare this to invite friends.")


# ---------------------------
# /deposit handler - guide user to webapp
# ---------------------------
async def deposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Instructs user to use the mini app. You can extend to accept a CLI /deposit <amount>
    but using the WebApp provides a much better UX (tx hash paste, auto-verify).
    """
    tg_user = update.effective_user
    # If WebApp available, send its button so user can open and deposit
    if getattr(config, "WEBAPP_URL", None):
        markup = build_webapp_markup_for_user(tg_user.id) if tg_user else None
        if markup:
            await update.message.reply_text("To deposit, open the WebApp (inside Telegram):", reply_markup=markup)
            return

    # fallback: show usage
    await update.message.reply_text("Usage: /deposit <amount_usd>. Example: /deposit 50\n\nOr open the Web App to deposit inside Telegram.")


# ---------------------------
# Optional helper: show status (rank/balance)
# ---------------------------
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Example command to show rank and cap left — uses services.user_service helper functions.
    """
    tg_user = update.effective_user
    if not tg_user:
        await update.message.reply_text("Unable to detect user.")
        return

    try:
        user = get_or_create_user(tg_user)
        # current_rank and earning_cap_left are expected to be implemented in services.user_service
        rank = current_rank(user.id)
        cap_left = earning_cap_left(user.id)
        msg = f"Your rank: {rank}\nEarning cap left (USD): {cap_left:.2f}"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("status_cmd failed: %s", e)
        await update.message.reply_text("Unable to fetch status right now.")


# ---------------------------
# Register all handlers with application
# ---------------------------
def register_user_handlers(app):
    """
    Register handlers related to user flows.
    Expects `app` to be telegram.ext.Application
    """
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_cmd))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("deposit", deposit_cmd))
    app.add_handler(CommandHandler("status", status_cmd))

    
