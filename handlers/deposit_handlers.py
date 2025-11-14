# handlers/deposit_handlers.py
from telegram.ext import Application, CommandHandler
from telegram import Update
from services.deposit_service import create_deposit
from services.user_service import get_or_create_user


async def deposit_cmd(update: Update, context):
    if not context.args:
        await update.message.reply_text("Usage: /deposit <amount_usd>. Example: /deposit 50")
        return
    try:
        amount = float(context.args[0])
    except Exception:
        await update.message.reply_text("Please provide a valid number. Example: /deposit 50")
        return

    user = get_or_create_user(update.effective_user)
    try:
        dep = create_deposit(user, amount)
    except Exception as e:
        await update.message.reply_text(str(e))
        return

    await update.message.reply_text(
        f"Deposit request recorded (ID: {dep.id}).\n"
        f"Split → MUSD: {dep.musd}, MSTC: {dep.mstc}.\n"
        f"An admin will approve it. You'll be active after approval."
    )


def register_deposit_handlers(app: Application):
    """Registers the deposit-related commands with the bot application."""
    app.add_handler(CommandHandler("deposit", deposit_cmd))
    app.add_handler(CommandHandler("activate", deposit_cmd))
