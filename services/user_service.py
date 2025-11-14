from db.session import SessionLocal
from db.models import User, Deposit
from sqlalchemy import select, func
from typing import Optional, Set
import datetime as dt
from config import GRACE_HOURS, EARNING_CAP_MULTIPLIER, REQUIREMENTS, Rank


def get_or_create_user(tg_user) -> User:
    with SessionLocal() as session:
        u = session.execute(select(User).where(User.telegram_id == tg_user.id)).scalar_one_or_none()
        if not u:
            u = User(telegram_id=tg_user.id, username=tg_user.username)
            session.add(u)
            session.commit()
            session.refresh(u)
        else:
            if u.username != tg_user.username:
                u.username = tg_user.username
                session.commit()
        return u


def set_referrer_if_first_time(user: User, referrer_tg_id: Optional[int]) -> Optional[User]:
    with SessionLocal() as session:
        u = session.get(User, user.id)
        if u.referred_by_id is not None:
            return None
        if not referrer_tg_id or referrer_tg_id == u.telegram_id:
            return None
        ref = session.execute(select(User).where(User.telegram_id == referrer_tg_id)).scalar_one_or_none()
        if not ref:
            return None
        u.referred_by_id = ref.id
        session.commit()
        return ref


def compute_downline(root_user: User) -> Set[int]:
    with SessionLocal() as session:
        visited = set()
        layer = [root_user.id]
        while layer:
            q = session.execute(select(User).where(User.referred_by_id.in_(layer))).scalars().all()
            next_layer = []
            for child in q:
                if child.id not in visited:
                    visited.add(child.id)
                    next_layer.append(child.id)
            layer = next_layer
        return visited


def team_business_usd(root_user: User) -> float:
    ids = compute_downline(root_user)
    if not ids:
        return 0.0
    with SessionLocal() as session:
        total = session.execute(
            select(func.coalesce(func.sum(Deposit.amount_usd), 0.0))
            .where(Deposit.user_id.in_(ids), Deposit.approved.is_(True))
        ).scalar_one()
        return float(total or 0.0)


def active_origin_count(root_user: User) -> int:
    ids = compute_downline(root_user)
    if not ids:
        return 0
    with SessionLocal() as session:
        count = session.execute(
            select(func.count(User.id)).where(User.id.in_(ids), User.is_active.is_(True))
        ).scalar_one()
        return int(count or 0)


def current_rank(user: User):
    if not user.is_active:
        return Rank.Origin
    tb = team_business_usd(user)
    act = active_origin_count(user)
    achieved = [Rank.Origin]
    for rank in [Rank.LifeChanger, Rank.Advisor, Rank.Visionary, Rank.Creator]:
        req = REQUIREMENTS[rank]
        if tb >= req["min_team_business"] and act >= req["active_origins_in_group"]:
            achieved.append(rank)
    return achieved[-1]


def earning_cap_left(user: User) -> float:
    cap = user.total_deposit_usd * EARNING_CAP_MULTIPLIER
    return max(0.0, cap - user.earned_total_usd)


def ensure_cap_flags(user: User):
    if not user.reactivation_required and earning_cap_left(user) <= 0.0:
        now = dt.datetime.utcnow()
        user.reactivation_required = True
        user.cap_reached_at = now
        user.reactivation_deadline_at = now + dt.timedelta(hours=GRACE_HOURS)
        with SessionLocal() as session:
            u = session.get(User, user.id)
            u.reactivation_required = True
            u.cap_reached_at = user.cap_reached_at
            u.reactivation_deadline_at = user.reactivation_deadline_at
            session.commit()


def reward_route_after_deadline(user: User) -> str:
    if not user.reactivation_required:
        return "credit"
    if user.reactivated_after_cap:
        return "credit"
    if user.reactivation_deadline_at and dt.datetime.utcnow() <= user.reactivation_deadline_at:
        return "grace_wait"
    return "redirect"
