from collections.abc import Callable, Iterator
from contextlib import ExitStack
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from signalscope.api.deps import require_role
from signalscope.core.config import get_settings
from signalscope.main import create_app
from signalscope.models import UserRole
from signalscope.seed import DEMO_PASSWORD
from signalscope.services.auth import AuthContext

AUTH = "/api/v1/auth"
PASSWORD = "Correct-Horse-42"


@pytest.fixture
def make_client(monkeypatch) -> Iterator[Callable[..., TestClient]]:
    """Build a client with extra settings, e.g. make_client(REFRESH_REUSE_GRACE_S="0")."""
    with ExitStack() as stack:

        def _make(**env: str) -> TestClient:
            for key, value in env.items():
                monkeypatch.setenv(key, value)
            get_settings.cache_clear()
            app = create_app()

            @app.get("/test/admin-only")
            async def _admin_only(_: Annotated[AuthContext, Depends(require_role(UserRole.ADMIN))]):
                return {"ok": True}

            return stack.enter_context(TestClient(app))

        yield _make


def signup(client, email="alice@example.com", password=PASSWORD, name="Alice"):
    return client.post(f"{AUTH}/signup", json={"email": email, "password": password, "display_name": name})


def login(client, email="alice@example.com", password=PASSWORD, remember=False):
    return client.post(f"{AUTH}/login", json={"email": email, "password": password, "remember": remember})


def cookie(client, name: str) -> str:
    return next(c.value for c in client.cookies.jar if c.name == name)


def use_cookies(client, **cookies: str) -> None:
    client.cookies.clear()
    for name, value in cookies.items():
        client.cookies.set(name, value)


def set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


# ---------------------------------------------------------------- signup & login


def test_signup_creates_account_and_sets_secure_cookies(client):
    response = signup(client)

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["email"] == "alice@example.com"
    assert user["display_name"] == "Alice"
    assert user["role"] == "user"
    assert "password_hash" not in user

    headers = set_cookie_headers(response)
    access = next(h for h in headers if h.startswith("ss_access="))
    refresh = next(h for h in headers if h.startswith("ss_refresh="))
    for header in (access, refresh):
        assert "HttpOnly" in header
        assert "samesite=lax" in header.lower()
    assert "Path=/api/v1/auth" in refresh  # refresh token never leaves the auth endpoints


def test_email_is_normalised_and_unique(client):
    assert signup(client, email="  Alice@Example.COM ").json()["user"]["email"] == "alice@example.com"

    response = signup(client, email="alice@example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert response.json()["error"]["field"] == "email"


@pytest.mark.parametrize(
    ("password", "fragment"),
    [
        ("short1!", "at least 10"),
        ("password123", "too common"),
        ("aaaaaaaaaaab", "repetitive"),
        ("alice-rocks-2026", "email"),
    ],
)
def test_signup_enforces_password_policy(client, password, fragment):
    response = signup(client, password=password)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "weak_password"
    assert error["field"] == "password"
    assert fragment in error["message"]


def test_signup_rejects_invalid_email(client):
    response = signup(client, email="not-an-email")

    assert response.status_code == 422
    assert response.json()["error"]["field"] == "email"


def test_login_and_me(client):
    signup(client)
    client.cookies.clear()

    response = login(client, email="ALICE@example.com")

    assert response.status_code == 200
    assert client.get(f"{AUTH}/me").json()["email"] == "alice@example.com"


def test_login_failures_do_not_reveal_whether_account_exists(client):
    signup(client)
    client.cookies.clear()

    wrong_password = login(client, password="Wrong-Password-99")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["code"] == unknown_email.json()["error"]["code"]
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


def test_remember_me_controls_cookie_persistence(client):
    signup(client)

    session_only = next(h for h in set_cookie_headers(login(client)) if h.startswith("ss_refresh="))
    persistent = next(
        h for h in set_cookie_headers(login(client, remember=True)) if h.startswith("ss_refresh=")
    )

    assert "Max-Age" not in session_only
    assert "Max-Age=2592000" in persistent  # 30 days


def test_me_requires_authentication(client):
    response = client.get(f"{AUTH}/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_update_profile(client):
    signup(client)

    assert client.patch(f"{AUTH}/me", json={"display_name": "  Bob  "}).json()["display_name"] == "Bob"
    assert client.patch(f"{AUTH}/me", json={"display_name": "   "}).status_code == 422


# ---------------------------------------------------------------- session bootstrap & refresh


def test_session_endpoint_for_guest_and_user(client):
    assert client.get(f"{AUTH}/session").json() == {"user": None}

    signup(client)

    assert client.get(f"{AUTH}/session").json()["user"]["email"] == "alice@example.com"


def test_session_endpoint_refreshes_transparently_when_access_cookie_missing(client):
    signup(client)
    refresh_token = cookie(client, "ss_refresh")
    use_cookies(client, ss_refresh=refresh_token)

    response = client.get(f"{AUTH}/session")

    assert response.json()["user"]["email"] == "alice@example.com"
    new_refresh = next(h for h in set_cookie_headers(response) if h.startswith("ss_refresh="))
    assert refresh_token not in new_refresh  # rotated
    assert any(h.startswith("ss_access=") for h in set_cookie_headers(response))


def test_expired_access_token_reports_token_expired(make_client):
    client = make_client(ACCESS_TOKEN_TTL_S="-10")
    signup(client)

    response = client.get(f"{AUTH}/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


def test_refresh_rotates_tokens(client):
    signup(client)
    old_refresh, old_access = cookie(client, "ss_refresh"), cookie(client, "ss_access")

    response = client.post(f"{AUTH}/refresh")

    assert response.status_code == 200
    assert cookie(client, "ss_refresh") != old_refresh
    assert cookie(client, "ss_access") != old_access
    assert client.get(f"{AUTH}/me").status_code == 200


def test_reusing_a_rotated_refresh_token_revokes_the_whole_session(make_client):
    client = make_client(REFRESH_REUSE_GRACE_S="0")
    signup(client)
    stolen = cookie(client, "ss_refresh")
    client.post(f"{AUTH}/refresh")
    legit_refresh, legit_access = cookie(client, "ss_refresh"), cookie(client, "ss_access")

    use_cookies(client, ss_refresh=stolen)
    reuse = client.post(f"{AUTH}/refresh")

    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "session_revoked"
    # The legitimate holder is signed out too — the family is burned.
    use_cookies(client, ss_refresh=legit_refresh, ss_access=legit_access)
    assert client.post(f"{AUTH}/refresh").status_code == 401
    use_cookies(client, ss_access=legit_access)
    assert client.get(f"{AUTH}/me").json()["error"]["code"] == "session_revoked"


def test_concurrent_refresh_within_grace_window_is_benign(client):
    signup(client)
    old = cookie(client, "ss_refresh")
    client.post(f"{AUTH}/refresh")
    current_refresh, current_access = cookie(client, "ss_refresh"), cookie(client, "ss_access")

    use_cookies(client, ss_refresh=old)
    race = client.post(f"{AUTH}/refresh")

    assert race.status_code == 401
    assert race.json()["error"]["code"] == "token_rotated"
    assert not any(h.startswith("ss_") for h in set_cookie_headers(race))  # cookies left alone
    use_cookies(client, ss_refresh=current_refresh, ss_access=current_access)
    assert client.post(f"{AUTH}/refresh").status_code == 200


def test_refresh_without_cookie(client):
    assert client.post(f"{AUTH}/refresh").json()["error"]["code"] == "not_authenticated"


# ---------------------------------------------------------------- logout & sessions


def test_logout_ends_session_immediately(client):
    signup(client)
    access = cookie(client, "ss_access")

    assert client.post(f"{AUTH}/logout").status_code == 200

    # Even a copied access token stops working at once (session checked on every request).
    client.cookies.clear()
    response = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {access}"})
    assert response.json()["error"]["code"] == "session_revoked"


def test_sessions_list_and_revoke_other_device(client):
    signup(client)  # device 1
    device1_access = cookie(client, "ss_access")
    client.cookies.clear()
    login(client)  # device 2 (current)

    sessions = client.get(f"{AUTH}/sessions").json()["sessions"]

    assert len(sessions) == 2
    assert [s["current"] for s in sessions].count(True) == 1
    other = next(s for s in sessions if not s["current"])
    assert other["device"]

    assert client.delete(f"{AUTH}/sessions/{other['id']}").status_code == 200
    assert len(client.get(f"{AUTH}/sessions").json()["sessions"]) == 1
    denied = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {device1_access}"})
    assert denied.status_code == 401


def test_revoking_unknown_session_is_404(client):
    signup(client)

    response = client.delete(f"{AUTH}/sessions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_logout_all(client):
    signup(client)
    first_access = cookie(client, "ss_access")
    login(client)

    assert client.post(f"{AUTH}/logout-all").status_code == 200

    assert client.get(f"{AUTH}/me").status_code == 401
    assert client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {first_access}"}).status_code == 401


def test_change_password(client):
    signup(client)
    other_device_access = cookie(client, "ss_access")
    client.cookies.clear()
    login(client)

    wrong = client.post(
        f"{AUTH}/change-password",
        json={"current_password": "nope-nope-nope", "new_password": "New-Secret-77"},
    )
    weak = client.post(
        f"{AUTH}/change-password", json={"current_password": PASSWORD, "new_password": "short"}
    )
    ok = client.post(
        f"{AUTH}/change-password", json={"current_password": PASSWORD, "new_password": "New-Secret-77"}
    )

    assert wrong.status_code == 400 and wrong.json()["error"]["field"] == "current_password"
    assert weak.status_code == 422 and weak.json()["error"]["field"] == "new_password"
    assert ok.status_code == 200
    assert client.get(f"{AUTH}/me").status_code == 200  # this device stays signed in
    assert (
        client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {other_device_access}"}).status_code
        == 401
    )
    client.cookies.clear()
    assert login(client).status_code == 401
    assert login(client, password="New-Secret-77").status_code == 200


# ---------------------------------------------------------------- abuse protection


def test_account_locks_after_repeated_failures(client):
    signup(client)
    client.cookies.clear()

    for _ in range(5):
        assert login(client, password="Wrong-Password-99").status_code == 401
    locked = login(client)  # even the correct password is refused while locked

    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "account_locked"
    assert "minute" in locked.json()["error"]["message"]


def test_login_is_rate_limited_per_ip(client):
    for _ in range(10):
        assert login(client, email="nobody@example.com").status_code == 401

    limited = login(client, email="nobody@example.com")

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) > 0


def test_cross_site_requests_with_cookies_are_blocked(client):
    signup(client)

    evil = client.post(f"{AUTH}/logout", headers={"Origin": "https://evil.example"})
    same_app = client.post(f"{AUTH}/logout", headers={"Origin": "http://localhost:5173"})

    assert evil.status_code == 403
    assert evil.json()["error"]["code"] == "csrf_rejected"
    assert same_app.status_code == 200


# ---------------------------------------------------------------- roles & seed


def test_role_guard(make_client):
    client = make_client(SEED_DEMO_USERS="true")

    assert client.get("/test/admin-only").status_code == 401
    login(client, email="demo@signalscope.dev", password=DEMO_PASSWORD)
    assert client.get("/test/admin-only").status_code == 403
    login(client, email="admin@signalscope.dev", password=DEMO_PASSWORD)
    assert client.get("/test/admin-only").json() == {"ok": True}


def test_seed_is_idempotent(make_client):
    make_client(SEED_DEMO_USERS="true")
    client = make_client(SEED_DEMO_USERS="true")  # second startup on the same database

    response = login(client, email="reviewer@signalscope.dev", password=DEMO_PASSWORD)

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "reviewer"


def test_guest_analysis_still_works_without_cookies(client, encode):
    response = client.post("/api/v1/analyze", files={"file": ("a.jpg", encode(), "image/jpeg")})

    assert response.status_code == 200
