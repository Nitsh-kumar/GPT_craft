"""Real TCP streaming: TestClient buffers bodies and cannot prove first-token timing."""
import contextlib
import json
import socket
import threading
import time
import httpx
import pytest
import uvicorn
from app.main import app


@contextlib.contextmanager
def live_server():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, lifespan='off', log_level='error', ws='none'))
    thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 3
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError('Local test server failed to start')
        time.sleep(.01)
    try:
        yield f'http://127.0.0.1:{port}'
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive(), 'Local streaming server did not shut down'


def test_first_content_arrives_before_provider_completes(registered, provider):
    _, headers = registered()
    provider.hold = True
    with live_server() as url, httpx.Client(base_url=url, trust_env=False, timeout=3) as client:
        try:
            with client.stream('POST', '/chat/stream', headers=headers, json={'message':'hello'}) as response:
                frames = (json.loads(line[6:]) for line in response.iter_lines() if line.startswith('data: '))
                assert next(frames)['type'] == 'start'
                assert next(frames) == {'type':'chunk', 'content':provider.text}
                assert not provider.release.is_set()
                provider.release.set()
                assert list(frames)[-1]['type'] == 'done'
        finally:
            provider.release.set()


def test_client_disconnect_cancels_provider_and_never_saves_partial_success(registered, provider):
    _, headers = registered()
    provider.hold = True
    with live_server() as url, httpx.Client(base_url=url, trust_env=False, timeout=3) as client:
        try:
            with client.stream('POST', '/chat/stream', headers=headers, json={'message':'hello'}) as response:
                frames = (json.loads(line[6:]) for line in response.iter_lines() if line.startswith('data: '))
                start = next(frames)
                assert next(frames)['type'] == 'chunk'
            assert provider.cancelled.wait(2), 'Disconnect did not cancel upstream generation'
            deadline = time.monotonic() + 2
            from app.db.session import SessionLocal
            from app.db.models import QuotaReservation
            while True:
                with SessionLocal() as db:
                    status = db.get(QuotaReservation, start['request_id']).status
                if status != 'pending': break
                assert time.monotonic() < deadline, 'Cancellation left a pending reservation'
                time.sleep(.01)
            assert status == 'cancelled'
            history = client.get(f"/chat/{start['conversation_id']}/history", headers=headers).json()
            assert [m['role'] for m in history] == ['user']
        finally:
            provider.release.set()
