import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    total_deposit_usd = Column(Float, default=0.0)
    earned_total_usd = Column(Float, default=0.0)
    musd_balance = Column(Float, default=0.0)
    mstc_balance = Column(Float, default=0.0)

    first_deposit_amount_usd = Column(Float, nullable=True)
    cap_reached_at = Column(DateTime, nullable=True)
    reactivation_deadline_at = Column(DateTime, nullable=True)
    reactivation_required = Column(Boolean, default=False)
    reactivated_after_cap = Column(Boolean, default=False)

    referred_by = relationship("User", remote_side=[id], backref="referrals")
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_usd = Column(Float, nullable=False)
    musd = Column(Float, default=0.0)
    mstc = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="deposits")


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    referred_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    deposit_id = Column(Integer, ForeignKey("deposits.id"), nullable=False)

    percent = Column(Float, nullable=False)
    amount_usd = Column(Float, nullable=False)
    status = Column(String, default="credited")
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    redirected_to_company = Column(Boolean, default=False)


class CompanyPool(Base):
    __tablename__ = "company_pool"

    id = Column(Integer, primary_key=True)
    amount_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
