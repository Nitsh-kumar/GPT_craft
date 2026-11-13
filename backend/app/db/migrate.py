"""Explicit, repeatable pre-deploy schema creation and legacy quota import.

Run with application traffic stopped: python -m app.db.migrate
No quota is reset on subsequent runs. Legacy tables are retained for rollback.
"""
from datetime import datetime, time, timedelta
from sqlalchemy import func, select, text
from app.ai.llm import PLAN_QUOTAS
from app.db.base import Base
from app.db.models import UserDailyLimit, DailyQuota, User, Plans, Conversation, Message
from app.db.crud_token import insert_once, utc_now
from app.db.session import engine, SessionLocal


def migrate(bind=engine):
    Base.metadata.create_all(bind)
    with SessionLocal(bind=bind) as db:
        if bind.dialect.name == 'postgresql':
            # These tables are internal to the privileged backend, never browser
            # Data API resources. Owners bypass RLS; public roles get no policies.
            for table in ('daily_quotas', 'quota_reservations', 'generation_details'):
                db.execute(text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
        # Include users without legacy daily rows: deleted/absent quota rows must
        # not erase request usage still evidenced by conversation history.
        today = utc_now().date()
        legacy = db.execute(select(UserDailyLimit.user_id, UserDailyLimit.date,
                                   func.min(UserDailyLimit.daily_limit))
                            .group_by(UserDailyLimit.user_id, UserDailyLimit.date)).all()
        imported = {(user_id, day): max(0, remaining) for user_id, day, remaining in legacy}
        for user_id, plan in db.execute(select(User.id, Plans.name).join(Plans, User.plan_id == Plans.id)):
            imported.setdefault((user_id, today), PLAN_QUOTAS.get(plan, PLAN_QUOTAS['free'])['tokens'])
        for (user_id, day), remaining in imported.items():
            if db.get(User, user_id) is None:
                continue
            start = datetime.combine(day, time.min)
            used = db.scalar(select(func.count(Message.id)).join(Conversation)
                             .where(Conversation.user_id == user_id, Message.role == 'user',
                                    Message.created_at >= start,
                                    Message.created_at < start + timedelta(days=1)))
            insert_once(db, DailyQuota, dict(user_id=user_id, date=day, tokens_remaining=remaining,
                        requests_used=used, burst_window=0, burst_count=0), ['user_id', 'date'])
        db.commit()
    from app.main import seed_default_plan
    seed_default_plan(bind)
    print('Schema and legacy quota import complete. Existing reservations/quotas preserved.')


if __name__ == '__main__':
    migrate()
