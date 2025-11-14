# services/deposit_service.py
from db.session import SessionLocal
from db.models import User, Deposit, CompanyPool
from sqlalchemy import select
from config import MIN_FIRST_DEPOSIT, SUBSEQUENT_MULTIPLE, MUSD_SPLIT, MSTC_SPLIT


def create_deposit(user: User, amount: float) -> Deposit:
    """
    Create a deposit request (not approved). Validates first/min and multiples.
    """
    with SessionLocal() as session:
        u = session.get(User, user.id)
        if u is None:
            raise ValueError("User not found in DB")

        first = u.total_deposit_usd <= 0.0
        if first and amount < MIN_FIRST_DEPOSIT:
            raise ValueError(f"First deposit must be at least ${MIN_FIRST_DEPOSIT}")

        if (not first) and (amount % SUBSEQUENT_MULTIPLE != 0):
            raise ValueError(f"Subsequent deposits must be in multiples of ${SUBSEQUENT_MULTIPLE}")

        musd = round(amount * MUSD_SPLIT, 2)
        mstc = round(amount * MSTC_SPLIT, 2)

        dep = Deposit(user_id=u.id, amount_usd=amount, musd=musd, mstc=mstc)
        session.add(dep)
        session.commit()
        session.refresh(dep)
        return dep


def approve_deposit(tg_id: int, dep_id: int) -> Deposit:
    """
    Approve a pending deposit for the user identified by tg_id.
    Returns the approved Deposit object.
    """
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.telegram_id == tg_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        dep = session.get(Deposit, dep_id)
        if not dep or dep.user_id != user.id:
            raise ValueError("Deposit not found for this user")

        if dep.approved:
            raise ValueError("Deposit already approved")

        # Approve & apply balances
        dep.approved = True
        user.total_deposit_usd += dep.amount_usd
        user.musd_balance += dep.musd
        user.mstc_balance += dep.mstc

        # Record first approved deposit if not set
        if user.first_deposit_amount_usd is None:
            user.first_deposit_amount_usd = dep.amount_usd

        # Activate user on approval
        user.is_active = True

        session.commit()
        session.refresh(dep)
        return dep
