import json
from uuid import uuid4
import pytest
from app.db.session import SessionLocal
from app.db.models import DailyQuota
from app.db.crud_token import utc_now


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


def test_sse_streams_and_settles(client, registered, provider):
    _, headers = registered()
    response = client.post('/chat/stream', headers=headers, json={'message':'hello'})
    frames = events(response)
    assert frames[0]['type'] == 'start'
    assert any(frame['type'] == 'chunk' for frame in frames)
    assert frames[-1]['type'] == 'done'
    assert frames[-1]['tokens_used'] == 42
    assert client.get('/chat/quota', headers=headers).json()['tokensRemaining'] == 4958


@pytest.mark.parametrize('path', ['/chat', '/chat/stream'])
def test_rejects_before_dispatch_when_quota_insufficient(client, registered, provider, path):
    data, headers = registered()
    with SessionLocal() as db:
        db.get(DailyQuota, (data['user']['id'], utc_now().date())).tokens_remaining = 1
        db.commit()
    assert client.post(path, headers=headers, json={'message':'hello'}).status_code == 402
    assert provider.calls == 0
    assert client.get('/chat/conversations', headers=headers).json() == []


def test_duplicate_request_cannot_dispatch_or_charge_twice(client, registered, provider):
    _, headers = registered()
    payload = {'message':'hello', 'request_id':str(uuid4())}
    assert client.post('/chat', headers=headers, json=payload).status_code == 200
    assert client.post('/chat', headers=headers, json=payload).status_code == 409
    assert provider.calls == 1
    assert client.get('/chat/quota', headers=headers).json()['tokensRemaining'] == 4958
