"""Atomic admission/settlement. No transaction spans a provider call."""
from datetime import datetime, timezone
from dataclasses import dataclass
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from app.ai.llm import PLAN_QUOTAS
from app.core.config import get_settings
from app.db.models import DailyQuota, QuotaReservation, Message, GenerationDetails, Conversation


@dataclass(frozen=True)
class AssistantReply:
    conversation_id: int
    content: str
    model: str
    mode: str


def utc_now():
    return datetime.now(timezone.utc)


def insert_once(db, model, values, keys):
    dialect = db.get_bind().dialect.name
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    db.execute(insert(model).values(**values).on_conflict_do_nothing(index_elements=keys))


class TokenUsageCRUD:
    @staticmethod
    def get_user_limit(db, user_id):
        return db.get(DailyQuota, (user_id, utc_now().date()))

    @staticmethod
    def create_user_limit(db, user_id, initial_limit=5000):
        today = utc_now().date()
        insert_once(db, DailyQuota, dict(user_id=user_id, date=today,
                    tokens_remaining=initial_limit, requests_used=0, burst_window=0, burst_count=0),
                    ["user_id", "date"])
        db.commit()
        return db.get(DailyQuota, (user_id, today))

    @staticmethod
    def quota(db, user_id, tier):
        allowance = PLAN_QUOTAS.get(tier, PLAN_QUOTAS["free"])
        row = TokenUsageCRUD.get_user_limit(db, user_id)
        if row is None:
            row = TokenUsageCRUD.create_user_limit(db, user_id, allowance["tokens"])
        result = dict(tokensRemaining=row.tokens_remaining,
                      requestsRemaining=max(0, allowance["requests"] - row.requests_used),
                      totalTokens=allowance["tokens"], totalRequests=allowance["requests"])
        db.commit()
        return result

    @staticmethod
    def reserve(db, user_id, tier, tokens, request_id=None):
        now = utc_now()
        epoch, day = int(now.timestamp()), now.date()
        window = epoch // 60
        allowance = PLAN_QUOTAS.get(tier, PLAN_QUOTAS["free"])
        insert_once(db, DailyQuota, dict(user_id=user_id, date=day,
                    tokens_remaining=allowance["tokens"], requests_used=0, burst_window=0, burst_count=0),
                    ["user_id", "date"])
        # Unobserved completion after process loss is conservatively charged. Never
        # refund a crashed call whose provider usage is unknown.
        db.execute(update(QuotaReservation).where(
            QuotaReservation.user_id == user_id, QuotaReservation.status == "pending",
            QuotaReservation.expires_at <= epoch).values(status="expired"))
        reservation_id = request_id or str(uuid4())
        db.add(QuotaReservation(id=reservation_id, user_id=user_id, date=day,
                               reserved_tokens=tokens, status="pending", expires_at=epoch + 120))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "This request was already submitted. Reload the conversation before retrying.")
        fresh_window = DailyQuota.burst_window != window
        changed = db.execute(update(DailyQuota).where(
            DailyQuota.user_id == user_id, DailyQuota.date == day,
            DailyQuota.tokens_remaining >= tokens,
            DailyQuota.requests_used < allowance["requests"],
            fresh_window | (DailyQuota.burst_count < get_settings().chat_burst_limit),
        ).values(tokens_remaining=DailyQuota.tokens_remaining - tokens,
                 requests_used=DailyQuota.requests_used + 1,
                 burst_window=window,
                 burst_count=case((fresh_window, 1), else_=DailyQuota.burst_count + 1)))
        if changed.rowcount != 1:
            db.rollback()
            row = db.get(DailyQuota, (user_id, day))
            if row is not None and row.requests_used >= allowance["requests"]:
                retry = 86400 - (epoch % 86400)
                raise HTTPException(429, "Daily request limit exceeded.", headers={"Retry-After": str(retry)})
            if row is not None and row.burst_window == window and row.burst_count >= get_settings().chat_burst_limit:
                raise HTTPException(429, "Too many requests. Please wait before retrying.",
                                    headers={"Retry-After": str(60 - epoch % 60)})
            raise HTTPException(402, "Insufficient token quota for this conversation and response.")
        db.commit()
        return reservation_id

    @staticmethod
    def finish(db, reservation_id, *, outcome, tokens_used=None, assistant=None):
        """Claim settlement exactly once, refund unused tokens, optionally save reply.

        tokens_used=None retains the full reservation (partial/unknown usage).
        Explicit 0 releases tokens on failure before any observable output.
        Accepted requests always consume one daily/burst request slot.
        """
        claimed = db.execute(update(QuotaReservation).where(
            QuotaReservation.id == reservation_id, QuotaReservation.status == "pending"
        ).values(status=outcome).returning(
            QuotaReservation.user_id, QuotaReservation.date, QuotaReservation.reserved_tokens
        )).first()
        if claimed is None:
            db.rollback()
            return None
        user_id, day, reserved = claimed
        actual = reserved if tokens_used is None else max(0, tokens_used)
        delta = actual - reserved
        before = db.scalar(select(DailyQuota.tokens_remaining).where(
            DailyQuota.user_id == user_id, DailyQuota.date == day
        ).with_for_update())
        remaining = db.execute(update(DailyQuota).where(
            DailyQuota.user_id == user_id, DailyQuota.date == day
        ).values(tokens_remaining=case(
            (DailyQuota.tokens_remaining >= delta, DailyQuota.tokens_remaining - delta),
            else_=0,
        )).returning(DailyQuota.tokens_remaining)).scalar_one()
        # Keep actual provider usage even if a provider violates the reserved
        # upper bound. Record the unfunded excess instead of hiding the overrun.
        unfunded = max(0, delta - before)
        db.execute(update(QuotaReservation).where(QuotaReservation.id == reservation_id)
                   .values(tokens_used=actual, unfunded_tokens=unfunded))
        if assistant:
            conversation = db.scalar(select(Conversation).where(
                Conversation.id == assistant.conversation_id,
                Conversation.user_id == user_id,
            ).with_for_update())
            if conversation is not None:
                message = Message(conversation_id=conversation.id, role="assistant", content=assistant.content)
                message.generation = GenerationDetails(model_used=assistant.model, mode_used=assistant.mode)
                db.add(message)
        db.commit()
        return actual, remaining
