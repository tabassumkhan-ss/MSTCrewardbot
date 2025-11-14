# bot.py
import logging
import asyncio
from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config

# Import your existing handler registration functions
from handlers.user_handlers import register_user_handlers, start as start_handler
from handlers.deposit_handlers import register_deposit_handlers
from handlers.admin_handlers import register_admin_handlers

# ----- Logging -----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ----- Utility: build webapp button markup for a user -----
def build_webapp_markup(telegram_id: int):
    """
    Return InlineKeyboardMarkup containing a button that opens the WebApp
    URL set in config.WEBAPP_URL with a `ref` query param set to the user's telegram id.
    """
    base = config.WEBAPP_URL.rstrip("/") if config.WEBAPP_URL else ""
    if not base:
        return None
    url = f"{base}/webapp?ref={telegram_id}"
    webapp_info = WebAppInfo(url=url)
    btn = InlineKeyboardButton(text="💳 Open Deposit Web App", web_app=webapp_info)
    return InlineKeyboardMarkup([[btn]])


# ----- New command handler: /openwebapp and /webapp -----
async def open_webapp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends a message with a WebApp button that opens the deposit page inside Telegram.
    Usage: /openwebapp
    """
    user = update.effective_user
    if not user:
        await update.message.reply_text("Unable to detect user.")
        return

    if not config.WEBAPP_URL:
        await update.message.reply_text("WebApp URL not configured on server.")
        return

    markup = build_webapp_markup(user.id)
    await update.message.reply_text(
        "Open the deposit Web App (inside Telegram):",
        reply_markup=markup
    )


# ----- Patch start handler to include webapp button (wrapper) -----
# We wrap your existing start handler so it still runs its logic but we then
# append the WebApp button (if configured).
async def start_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # call your existing start (which creates user etc)
    try:
        # user_handlers.start expects (update, context)
        await start_handler(update, context)
    except Exception:
        # If existing start throws, log but continue to try to send webapp button
        logger.exception("error in original start handler")

    # send a separate message with webapp button (so original reply remains as-is)
    if config.WEBAPP_URL:
        try:
            user = update.effective_user
            markup = build_webapp_markup(user.id)
            if markup:
                await update.message.reply_text(
                    "Quick access — open the deposit Web App:",
                    reply_markup=markup
                )
        except Exception:
            logger.exception("failed to send webapp button")


# ----- Main registration function -----
def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in config.py / .env")

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Register your existing handlers
    try:
        register_user_handlers(app)
    except Exception:
        logger.exception("Failed to register user handlers")
    try:
        register_deposit_handlers(app)
    except Exception:
        logger.exception("Failed to register deposit handlers")
    try:
        register_admin_handlers(app)
    except Exception:
        logger.exception("Failed to register admin handlers")

    # Replace the /start handler with our wrapper that also sends webapp button
    # Remove any existing start handler if present and add wrapper
    app.add_handler(CommandHandler("start", start_wrapper))

    # Add new webapp commands
    app.add_handler(CommandHandler("openwebapp", open_webapp_cmd))
    app.add_handler(CommandHandler("webapp", open_webapp_cmd))

    # Optional helper command for convenience
    app.add_handler(CommandHandler("open", open_webapp_cmd))

    logger.info("Starting bot (polling).")
    print("Bot is running... CTRL+C to stop")

    # Run the bot (polling). Use close_loop=False if you want to reuse loop for other tasks
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
