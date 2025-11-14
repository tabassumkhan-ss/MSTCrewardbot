# handlers/admin_handlers.py
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.constants import ParseMode
from db.session import SessionLocal
from db.models import Deposit, User
from config import ADMIN_IDS
from services.deposit_service import approve_deposit
from services.reward_service import credit_reward

def admin_only(func):
    async def wrapper(update: Update, context):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("Admins only.")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def pending_cmd(update: Update, context):
    with SessionLocal() as session:
        rows = session.query(Deposit).filter(Deposit.approved == False).order_by(Deposit.created_at.asc()).all()
    if not rows:
        await update.message.reply_text("No pending deposits.")
        return
    lines = ["<b>Pending Deposits</b>"]
    for d in rows:
        # Use getattr checks to avoid attribute access errors in some states
        tg = getattr(d.user, "telegram_id", "unknown")
        lines.append(f"ID {d.id}: tg {tg} — ${d.amount_usd:.2f} (MUSD {d.musd}, MSTC {d.mstc})")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@admin_only
async def approve_deposit_cmd(update: Update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /approve_deposit <telegram_id> <deposit_id>")
        return
    try:
        tg_id = int(context.args[0])
        dep_id = int(context.args[1])
    except Exception:
        await update.message.reply_text("IDs must be numbers.")
        return

    try:
        dep = approve_deposit(tg_id, dep_id)
    except Exception as e:
        await update.message.reply_text(str(e))
        return

    # after approval, process reward to direct referrer (if any)
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == dep.user_id).one()
        if user.referred_by_id:
            ref = session.query(User).get(user.referred_by_id)
            # credit_reward handles cap/grace/redirect logic
            credit_reward(ref, user, dep)

    await update.message.reply_text(f"Approved deposit {dep.id} for {tg_id}. User active=Yes. Referral processed.")


def register_admin_handlers(app: Application):
    """Register admin command handlers."""
    app.add_handler(CommandHandler("pending", pending_cmd))
    app.add_handler(CommandHandler("approve_deposit", approve_deposit_cmd))
