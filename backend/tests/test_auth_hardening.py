"""Offline regression tests for auth, Google OAuth, config secrets, and JWKS hardening."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from jose.constants import ALGORITHMS

from app.core import security as security_module
from app.core.config import Settings, get_settings, validate_runtime_secret_key
from app.core.security import SecurityService
from app.db.models import DailyQuota, OAuthAccount, User
from app.db.session import SessionLocal


def _generate_rsa_keypair(kid: str) -> tuple[bytes, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_jwk = jwk.construct(public_pem, ALGORITHMS.RS256).to_dict()
    public_jwk["kid"] = kid
    public_jwk["use"] = "sig"
    public_jwk["alg"] = "RS256"
    return private_pem, public_jwk


def _sign_supabase_rs256(
    private_pem: bytes,
    kid: str,
    *,
    email: str = "supa@example.com",
    sub: str = "supa-uid-1",
    aud: str | None = "authenticated",
) -> str:
    now = datetime.now(timezone.utc)
    claims: dict = {
        "email": email,
        "sub": sub,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "user_metadata": {"name": "Supa User"},
    }
    if aud is not None:
        claims["aud"] = aud
    return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": kid})


def test_auth_me_requires_bearer_header_and_rejects_query_token(client, registered):
    data, headers = registered()
    token = data["accessToken"]

    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", params={"token": token}).status_code == 401

    res = client.get("/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "alice@example.com"


def test_get_user_by_token_has_no_daily_quota_side_effect_and_rejects_inactive_early(
    client, monkeypatch
):
    secret = "supabase-hs256-offline-test-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    get_settings.cache_clear()

    # Create an active user via register (note: register does not create DailyQuota)
    reg = client.post(
        "/auth/register",
        json={"name": "Original Name", "email": "readonly@example.com", "password": "password123"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]
    token = reg.json()["accessToken"]

    # Calling GET /auth/me must NOT write a DailyQuota row
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    with SessionLocal() as db:
        assert db.query(DailyQuota).filter_by(user_id=user_id).count() == 0

        # Deactivate user and clear supabase_uid to verify email-fallback path does not mutate it
        user = db.get(User, user_id)
        user.is_active = False
        user.supabase_uid = None
        db.commit()

    # Inactive user authenticated via Supabase token must get 403 without mutating supabase_uid or DailyQuota
    supa_token = jwt.encode(
        {
            "email": "readonly@example.com",
            "sub": "sub-should-not-bind",
            "aud": "authenticated",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "user_metadata": {"name": "Should Not Overwrite"},
        },
        secret,
        algorithm="HS256",
    )
    inactive_res = client.get("/auth/me", headers={"Authorization": f"Bearer {supa_token}"})
    assert inactive_res.status_code == 403
    assert inactive_res.json()["detail"] == "User account is inactive"

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.supabase_uid is None
        assert user.name == "Original Name"
        assert db.query(DailyQuota).filter_by(user_id=user_id).count() == 0


def test_google_oauth_callback_uses_fragment_handoff_and_blocks_inactive_users(
    client, monkeypatch
):
    from app.api.routes import google_oauth

    # Active user without prior OAuthAccount -> links account & redirects with #access_token=
    with SessionLocal() as db:
        active_user = User(
            name="OAuth Active",
            email="oauth-active@example.com",
            hashed_password=None,
            plan_id=1,
            is_active=True,
        )
        db.add(active_user)
        db.commit()

    async def fake_authorize_active(_request):
        return {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_at": 1999999999,
            "userinfo": {
                "email": "oauth-active@example.com",
                "name": "OAuth Active",
                "sub": "google-sub-active",
            },
        }

    monkeypatch.setattr(google_oauth.oauth.google, "authorize_access_token", fake_authorize_active)
    res = client.get("/auth/google/callback", follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    parsed = urlparse(location)
    assert parsed.path == "/auth-success"
    assert "token=" not in parsed.query
    fragment_params = parse_qs(parsed.fragment)
    assert "access_token" in fragment_params
    issued_token = fragment_params["access_token"][0]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {issued_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "oauth-active@example.com"

    # Now deactivate that linked user -> callback must refuse token & not refresh OAuthAccount
    with SessionLocal() as db:
        user = db.query(User).filter_by(email="oauth-active@example.com").one()
        user.is_active = False
        db.commit()

    async def fake_authorize_linked_inactive(_request):
        return {
            "access_token": "new-google-token-should-not-save",
            "userinfo": {
                "email": "oauth-active@example.com",
                "name": "OAuth Active",
                "sub": "google-sub-active",
            },
        }

    monkeypatch.setattr(
        google_oauth.oauth.google, "authorize_access_token", fake_authorize_linked_inactive
    )
    res_linked_inactive = client.get("/auth/google/callback", follow_redirects=False)
    assert res_linked_inactive.status_code in (302, 307)
    loc_inactive = res_linked_inactive.headers["location"]
    assert "/login?error=account_inactive" in loc_inactive
    assert "access_token" not in loc_inactive

    with SessionLocal() as db:
        acct = db.query(OAuthAccount).filter_by(provider_user_id="google-sub-active").one()
        assert acct.access_token == "google-access-token"

    # Unlinked inactive user matched by email -> must refuse token & not create OAuthAccount
    with SessionLocal() as db:
        db.add(
            User(
                name="Inactive Email User",
                email="oauth-inactive@example.com",
                hashed_password=None,
                plan_id=1,
                is_active=False,
            )
        )
        db.commit()

    async def fake_authorize_email_inactive(_request):
        return {
            "access_token": "should-not-link",
            "userinfo": {
                "email": "oauth-inactive@example.com",
                "name": "Inactive Email User",
                "sub": "google-sub-inactive",
            },
        }

    monkeypatch.setattr(
        google_oauth.oauth.google, "authorize_access_token", fake_authorize_email_inactive
    )
    res_email_inactive = client.get("/auth/google/callback", follow_redirects=False)
    assert res_email_inactive.status_code in (302, 307)
    assert "/login?error=account_inactive" in res_email_inactive.headers["location"]
    with SessionLocal() as db:
        assert db.query(OAuthAccount).filter_by(provider_user_id="google-sub-inactive").count() == 0


def test_google_oauth_error_redirect_strips_raw_exception_details(client, monkeypatch):
    from app.api.routes import google_oauth

    async def fake_authorize_boom(_request):
        raise RuntimeError("sensitive internal db connection string leaked")

    monkeypatch.setattr(google_oauth.oauth.google, "authorize_access_token", fake_authorize_boom)
    res = client.get("/auth/google/callback", follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    parsed = urlparse(location)
    assert parsed.path == "/login"
    assert parse_qs(parsed.query) == {"error": ["auth_failed"]}
    assert "details" not in location
    assert "sensitive" not in location


def test_config_rejects_placeholder_secret_keys_when_debug_false():
    for placeholder in (
        "your-secret-key-change-in-production",
        "replace_with_a_new_random_secret",
        "",
        "changeme",
    ):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(_env_file=None, debug=False, secret_key=placeholder)

    # Debug mode allows local placeholder defaults
    dev_settings = Settings(
        _env_file=None, debug=True, secret_key="your-secret-key-change-in-production"
    )
    assert dev_settings.debug is True

    # Explicit non-placeholder test secret works with debug=False
    test_settings = Settings(_env_file=None, debug=False, secret_key="offline-test-secret")
    validate_runtime_secret_key(test_settings)


def test_supabase_jwks_ttl_expiry_kid_rotation_and_audience_validation(monkeypatch):
    priv_1, jwk_1 = _generate_rsa_keypair("kid-1")
    priv_2, jwk_2 = _generate_rsa_keypair("kid-2")

    clock = {"now": 1000.0}
    served_jwks = {"keys": [jwk_1]}
    fetch_count = {"calls": 0}

    class FakeResponse:
        status_code = 200

        def __init__(self, payload: dict):
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    def fake_httpx_get(url: str, timeout: float = 5.0):
        assert url == "https://offline.supabase.invalid/auth/v1/.well-known/jwks.json"
        fetch_count["calls"] += 1
        return FakeResponse(served_jwks)

    monkeypatch.setenv("SUPABASE_URL", "https://offline.supabase.invalid")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "hs256-offline-secret")
    get_settings.cache_clear()
    monkeypatch.setattr(security_module, "_JWKS_CACHE", None)
    monkeypatch.setattr(security_module.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(security_module.httpx, "get", fake_httpx_get)

    # 1. First decode fetches JWKS and caches it
    tok_1 = _sign_supabase_rs256(priv_1, "kid-1")
    claims_1 = SecurityService.decode_token_claims(tok_1)
    assert claims_1 is not None and claims_1["email"] == "supa@example.com"
    assert fetch_count["calls"] == 1

    # 2. Second decode within TTL uses cache without HTTP fetch
    clock["now"] += 30.0
    assert SecurityService.decode_token_claims(tok_1) is not None
    assert fetch_count["calls"] == 1

    # 3. Unknown kid triggers immediate JWKS refresh even before TTL expires
    served_jwks = {"keys": [jwk_1, jwk_2]}
    tok_2 = _sign_supabase_rs256(priv_2, "kid-2", email="rotated@example.com")
    claims_2 = SecurityService.decode_token_claims(tok_2)
    assert claims_2 is not None and claims_2["email"] == "rotated@example.com"
    assert fetch_count["calls"] == 2

    # 4. Advancing past TTL expires cache and triggers refresh
    clock["now"] += security_module._JWKS_CACHE_TTL_SECONDS + 1.0
    assert SecurityService.decode_token_claims(tok_2) is not None
    assert fetch_count["calls"] == 3

    # 5. Audience validation: JWKS tokens with wrong or missing audience are rejected
    bad_aud_rs256 = _sign_supabase_rs256(priv_2, "kid-2", aud="other-service")
    no_aud_rs256 = _sign_supabase_rs256(priv_2, "kid-2", aud=None)
    assert SecurityService.decode_token_claims(bad_aud_rs256) is None
    assert SecurityService.decode_token_claims(no_aud_rs256) is None

    # 6. Audience validation: symmetric HS256 Supabase tokens also require aud='authenticated'
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    valid_hs256 = jwt.encode(
        {"email": "hs@example.com", "aud": "authenticated", "exp": exp},
        "hs256-offline-secret",
        algorithm="HS256",
    )
    bad_aud_hs256 = jwt.encode(
        {"email": "hs@example.com", "aud": "anon", "exp": exp},
        "hs256-offline-secret",
        algorithm="HS256",
    )
    no_aud_hs256 = jwt.encode(
        {"email": "hs@example.com", "exp": exp},
        "hs256-offline-secret",
        algorithm="HS256",
    )
    assert SecurityService.decode_token_claims(valid_hs256)["email"] == "hs@example.com"
    assert SecurityService.decode_token_claims(bad_aud_hs256) is None
    assert SecurityService.decode_token_claims(no_aud_hs256) is None
