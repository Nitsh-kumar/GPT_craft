from app.db.session import SessionLocal
from app.db.models import User


def test_health(client):
    assert client.get('/health').json()['status'] == 'healthy'


def test_register_login_and_inactive_user(client, registered):
    data, headers = registered()
    assert data['user']['plan'] == 'free'
    login = client.post('/auth/login', json={'email':'alice@example.com', 'password':'password123'})
    assert login.status_code == 200
    assert login.json()['accessToken']
    with SessionLocal() as db:
        user = db.get(User, data['user']['id'])
        user.is_active = False
        db.commit()
    assert client.get('/chat/quota', headers=headers).status_code == 403


def test_conversation_ownership_persistence_and_usage_survive_deletion(client, registered, provider):
    _, headers = registered()
    _, other = registered('other@example.com')
    response = client.post('/chat', headers=headers, json={'message':'hello', 'mode':'code'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['response'] == provider.text
    assert result['tokens_used'] == 42
    assert result['tokens_remaining'] == 4958
    assert result['model_used'] == 'openai/gpt-oss-20b'
    assert result['mode_used'] == 'code'
    conversation_id = result['conversation_id']
    history = client.get(f'/chat/{conversation_id}/history', headers=headers).json()
    assert [m['role'] for m in history] == ['user', 'assistant']
    assert history[-1]['model_used'] == 'openai/gpt-oss-20b'
    assert client.get(f'/chat/{conversation_id}/history', headers=other).status_code == 404
    assert client.delete(f'/chat/{conversation_id}', headers=other).status_code == 404
    assert client.delete(f'/chat/{conversation_id}', headers=headers).status_code == 204
    quota = client.get('/chat/quota', headers=headers).json()
    assert quota['requestsRemaining'] == 49
    assert quota['tokensRemaining'] == 4958


def test_model_catalog_matches_routing_and_legacy_alias(client, registered, provider):
    _, headers = registered()
    catalog = client.get('/chat/models').json()
    assert {m['id'] for m in catalog} == {'openai/gpt-oss-20b', 'openai/gpt-oss-120b'}
    locked = client.post('/chat', headers=headers, json={'message':'hello', 'model':'openai/gpt-oss-120b'})
    assert locked.status_code == 403
    assert provider.calls == 0
    invalid = client.post('/chat', headers=headers, json={'message':'hello', 'model':'invented-model'})
    assert invalid.status_code == 422
    assert provider.calls == 0
    response = client.post('/chat', headers=headers, json={'message':'hello', 'model':'llama3-8b-8192'})
    assert response.json()['model_used'] == 'openai/gpt-oss-20b'


def test_paid_model_access_uses_trusted_fixture_not_public_upgrade(client, registered, provider):
    data, headers = registered()
    with SessionLocal() as db:
        db.get(User, data['user']['id']).plan_id = 3
        db.commit()
    result = client.post('/chat', headers=headers, json={'message':'hello', 'model':'openai/gpt-oss-120b'})
    assert result.status_code == 200
    assert result.json()['model_used'] == 'openai/gpt-oss-120b'


def test_blank_message_rejected(client, registered, provider):
    _, headers = registered()
    assert client.post('/chat', headers=headers, json={'message':''}).status_code == 422
    assert provider.calls == 0
