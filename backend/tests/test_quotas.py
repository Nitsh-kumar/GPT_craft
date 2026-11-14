from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
import pytest
from fastapi import HTTPException
from app.db.session import SessionLocal
from app.db.models import DailyQuota, UserDailyLimit
from app.db.crud_token import TokenUsageCRUD, utc_now


@pytest.mark.parametrize('path', ['/chat', '/chat/stream'])
def test_daily_request_limit_rejects_before_dispatch(client, registered, provider, path):
    data, headers = registered()
    with SessionLocal() as db:
        db.get(DailyQuota, (data['user']['id'], utc_now().date())).requests_used = 50
        db.commit()
    response = client.post(path, headers=headers, json={'message':'hello'})
    assert response.status_code == 429
    assert int(response.headers['retry-after']) > 0
    assert provider.calls == 0


def test_burst_limit_is_enforced_and_has_retry_after(client, registered, provider, monkeypatch):
    monkeypatch.setenv('CHAT_BURST_LIMIT', '1')
    from app.core.config import get_settings
    get_settings.cache_clear()
    _, headers = registered()
    assert client.post('/chat', headers=headers, json={'message':'hello'}).status_code == 200
    limited = client.post('/chat/stream', headers=headers, json={'message':'hello'})
    assert limited.status_code == 429
    assert int(limited.headers['retry-after']) > 0
    assert provider.calls == 1


def test_prompt_history_must_fit_available_budget(client, registered, provider):
    _, headers = registered()
    response = client.post('/chat', headers=headers, json={'message':'x' * 6000})
    assert response.status_code == 402
    assert provider.calls == 0


@pytest.mark.parametrize('limit_kind', ['tokens', 'requests', 'first_request'])
def test_concurrent_admission_and_idempotent_settlement(registered, limit_kind):
    data, _ = registered()
    user_id = data['user']['id']
    with SessionLocal() as db:
        quota = db.get(DailyQuota, (user_id, utc_now().date()))
        if limit_kind == 'first_request':
            db.delete(quota)
        elif limit_kind == 'tokens':
            quota.tokens_remaining = 100
        else:
            quota.requests_used = 49
        db.commit()
    barrier = Barrier(2)
    def reserve():
        with SessionLocal() as db:
            barrier.wait(timeout=5)
            try:
                return TokenUsageCRUD.reserve(db, user_id, 'free', 100)
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    accepted = [r for r in results if isinstance(r, str)]
    assert len(accepted) == (2 if limit_kind == 'first_request' else 1)
    with SessionLocal() as db:
        assert db.query(DailyQuota).filter_by(user_id=user_id).count() == 1
        TokenUsageCRUD.finish(db, accepted[0], outcome='succeeded', tokens_used=42)
        assert TokenUsageCRUD.finish(db, accepted[0], outcome='succeeded', tokens_used=42) is None
        quota = TokenUsageCRUD.quota(db, user_id, 'free')
        if limit_kind == 'tokens':
            assert quota['tokensRemaining'] == 58
        if limit_kind == 'requests':
            assert quota['requestsRemaining'] == 0


def test_utc_rollover_starts_new_allowance(client, registered, monkeypatch):
    import app.db.crud_token as module
    data, headers = registered()
    monkeypatch.setattr(module, 'utc_now', lambda: datetime(2030, 1, 1, 23, 59, tzinfo=timezone.utc))
    with SessionLocal() as db:
        TokenUsageCRUD.reserve(db, data['user']['id'], 'free', 100)
    assert client.get('/chat/quota', headers=headers).json()['tokensRemaining'] == 4900
    monkeypatch.setattr(module, 'utc_now', lambda: datetime(2030, 1, 2, 0, 0, tzinfo=timezone.utc))
    assert client.get('/chat/quota', headers=headers).json()['tokensRemaining'] == 5000


def test_migration_consolidates_duplicates_without_refilling(registered):
    from app.db.migrate import migrate
    data, _ = registered()
    with SessionLocal() as db:
        db.query(DailyQuota).delete()
        db.add_all([UserDailyLimit(user_id=data['user']['id'], date=utc_now().date(), daily_limit=n)
                    for n in [5000, 2000]])
        db.commit()
    migrate()
    with SessionLocal() as db:
        assert TokenUsageCRUD.quota(db, data['user']['id'], 'free')['tokensRemaining'] == 2000
        TokenUsageCRUD.reserve(db, data['user']['id'], 'free', 100)
    migrate()
    with SessionLocal() as db:
        assert TokenUsageCRUD.quota(db, data['user']['id'], 'free')['tokensRemaining'] == 1900


def test_provider_overrun_keeps_actual_usage_without_negative_allowance(registered):
    from app.db.models import QuotaReservation
    data, _ = registered()
    with SessionLocal() as db:
        quota = db.get(DailyQuota, (data['user']['id'], utc_now().date()))
        quota.tokens_remaining = 100
        db.commit()
        request_id = TokenUsageCRUD.reserve(db, data['user']['id'], 'free', 100)
        assert TokenUsageCRUD.finish(db, request_id, outcome='succeeded', tokens_used=142) == (142, 0)
        row = db.get(QuotaReservation, request_id)
        assert row.tokens_used == 142
        assert row.unfunded_tokens == 42


def test_deleted_conversation_id_cannot_leak_reply_to_new_owner(client, registered):
    from app.db.models import Conversation
    from app.db.crud_token import AssistantReply
    a, _ = registered()
    b, headers_b = registered('bob@example.com')
    with SessionLocal() as db:
        original = Conversation(user_id=a['user']['id'], title='A private conversation')
        db.add(original)
        db.commit()
        conversation_id = original.id
        reservation = TokenUsageCRUD.reserve(db, a['user']['id'], 'free', 100)
        db.delete(original)
        db.commit()
        db.add(Conversation(id=conversation_id, user_id=b['user']['id'], title='B conversation'))
        db.commit()
        TokenUsageCRUD.finish(db, reservation, outcome='succeeded', tokens_used=42,
                              assistant=AssistantReply(conversation_id, 'PRIVATE A RESPONSE', 'test-model', 'standard'))
    assert client.get(f'/chat/{conversation_id}/history', headers=headers_b).json() == []
