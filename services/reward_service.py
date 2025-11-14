# services/reward_service.py
from db.session import SessionLocal
from db.models import User, Reward, CompanyPool, Deposit
from config import RANK_REWARD_PCT, EARNING_CAP_MULTIPLIER
from services.user_service import current_rank, earning_cap_left, ensure_cap_flags, reward_route_after_deadline

def credit_reward(referrer: User, referred: User, dep: Deposit):
    """
    Decide how to handle a referral reward for `referrer` when `referred`'s deposit `dep` is approved.
    This implements:
      - rank-based percent
      - respect earning cap (3x)
      - grace window behavior (grace_wait / redirect)
      - credit to referrer.musd_balance and update earned_total_usd
      - log Reward records and add to CompanyPool when redirected
    """
    # Load fresh DB state for referrer inside a session
    with SessionLocal() as session:
        ref = session.get(User, referrer.id)
        # compute route: "credit", "grace_wait", or "redirect"
        route = reward_route_after_deadline(ref)
        rank = current_rank(ref)
        pct = RANK_REWARD_PCT.get(rank, 0.0)
        gross = dep.amount_usd * pct

        # grace: don't credit or redirect, just log a grace_wait reward
        if route == "grace_wait":
            r = Reward(
                referrer_id=ref.id,
                referred_id=referred.id,
                deposit_id=dep.id,
                percent=pct,
                amount_usd=0.0,
                status="grace_wait",
                redirected_to_company=False,
            )
            session.add(r)
            session.commit()
            return

        # redirect: add gross to company pool and log reward as redirected
        if route == "redirect":
            cp = CompanyPool(amount_usd=gross)
            session.add(cp)
            r = Reward(
                referrer_id=ref.id,
                referred_id=referred.id,
                deposit_id=dep.id,
                percent=pct,
                amount_usd=0.0,
                status="redirected",
                redirected_to_company=True,
            )
            session.add(r)
            session.commit()
            return

        # credit path: apply cap
        cap_left = earning_cap_left(ref)
        amount = min(gross, cap_left)

        r = Reward(
            referrer_id=ref.id,
            referred_id=referred.id,
            deposit_id=dep.id,
            percent=pct,
            amount_usd=amount,
            status="credited",
            redirected_to_company=False,
        )
        session.add(r)

        if amount > 0:
            ref.musd_balance = (ref.musd_balance or 0.0) + amount
            ref.earned_total_usd = (ref.earned_total_usd or 0.0) + amount

        session.commit()

        # If this credit exhausted the cap, set cap flags (starts grace window)
        ensure_cap_flags(ref)
        session.commit()
