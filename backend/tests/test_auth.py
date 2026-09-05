import time

import pytest
from fastapi.testclient import TestClient

from app.security import COOLDOWN_SECONDS, MAX_ATTEMPTS, SESSION_COOKIE, sign_user_id
from tests.conftest import PASSWORD

OTHER = {"email": "other@example.com", "password": "another-long-enough-password"}


def register(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


# ── registration and login ────────────────────────────────────────────


def test_registration_creates_an_account_and_signs_it_in(anon: TestClient):
    response = register(anon, "new@example.com")
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert anon.get("/auth/me").json()["email"] == "new@example.com"


def test_the_session_cookie_is_httponly_so_script_cannot_read_it(anon: TestClient):
    """The account holds PHQ-8 responses; an XSS bug must not reach them."""
    response = register(anon, "cookie@example.com")
    header = response.headers["set-cookie"]
    assert SESSION_COOKIE in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header


def test_the_password_is_never_stored_or_returned_in_clear(anon: TestClient, db_session):
    from app.db.models import User

    register(anon, "hashed@example.com")
    with db_session() as db:
        user = db.query(User).filter(User.email == "hashed@example.com").one()
    assert user.password_hash is not None
    assert PASSWORD not in user.password_hash
    assert user.password_hash.startswith("$argon2")


def test_email_is_normalised_so_case_does_not_create_a_second_account(anon: TestClient):
    register(anon, "Mixed@Example.com")
    anon.post("/auth/logout")
    response = anon.post("/auth/login", json={"email": "mixed@example.com", "password": PASSWORD})
    assert response.status_code == 200


def test_a_short_password_is_refused_at_registration(anon: TestClient):
    assert register(anon, "short@example.com", "abc").status_code == 422


def test_login_signs_in_an_existing_account(anon: TestClient):
    register(anon, "login@example.com")
    anon.post("/auth/logout")

    response = anon.post("/auth/login", json={"email": "login@example.com", "password": PASSWORD})
    assert response.status_code == 200
    assert anon.get("/auth/me").status_code == 200


# ── not leaking which addresses exist ─────────────────────────────────


def test_a_wrong_password_and_an_unknown_email_fail_identically(anon: TestClient):
    """Otherwise the login form is an oracle for who has an account."""
    register(anon, "known@example.com")
    anon.post("/auth/logout")

    wrong = anon.post("/auth/login", json={"email": "known@example.com", "password": "wrong-password"})
    unknown = anon.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_registering_a_taken_address_gives_the_same_message(anon: TestClient):
    register(anon, "taken@example.com")
    anon.post("/auth/logout")

    duplicate = anon.post("/auth/register", json={"email": "taken@example.com", "password": PASSWORD})
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == ("That email and password combination was not recognised.")


# ── cookies ───────────────────────────────────────────────────────────


def test_a_tampered_cookie_is_rejected(api: TestClient):
    api.cookies.set(SESSION_COOKIE, sign_user_id("someone-else")[:-3] + "xxx")
    assert api.get("/auth/me").status_code == 401


def test_a_cookie_signed_for_a_deleted_account_is_rejected(anon: TestClient):
    """A valid signature over an id nobody owns must not authenticate."""
    anon.cookies.set(SESSION_COOKIE, sign_user_id("00000000-0000-4000-8000-ffffffffffff"))
    assert anon.get("/auth/me").status_code == 401


def test_an_expired_cookie_is_rejected(anon: TestClient, monkeypatch):
    """Forge a token stamped fifteen days ago; the maximum age is fourteen."""
    from itsdangerous import TimestampSigner

    fifteen_days_ago = int(time.time()) - 15 * 24 * 3600
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: fifteen_days_ago)
    stale = sign_user_id("whoever")
    monkeypatch.undo()

    anon.cookies.set(SESSION_COOKIE, stale)
    assert anon.get("/auth/me").status_code == 401


def test_logout_clears_the_session(api: TestClient):
    assert api.get("/auth/me").status_code == 200
    assert api.post("/auth/logout").status_code == 204
    api.cookies.clear()
    assert api.get("/auth/me").status_code == 401


# ── everything is protected ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/sessions"),
        ("get", "/sessions"),
        ("get", "/sessions/any-id"),
        ("post", "/sessions/any-id/readings"),
        ("post", "/sessions/any-id/end"),
        ("delete", "/sessions/any-id"),
        ("delete", "/users/me/data"),
        ("post", "/checkins"),
        ("get", "/checkins"),
        ("get", "/trends"),
    ],
)
def test_every_personal_endpoint_refuses_an_anonymous_request(anon: TestClient, method: str, path: str):
    kwargs = {"json": {}} if method == "post" else {}
    response = getattr(anon, method)(path, **kwargs)
    assert response.status_code == 401, f"{method.upper()} {path} was reachable"


def test_prediction_endpoints_stay_open(anon: TestClient):
    """They hold no personal data and the evaluation harness drives them."""
    response = anon.post("/predict/text", json={"text": "hello"})
    assert response.status_code != 401


# ── the isolation that matters most ───────────────────────────────────


def test_one_account_cannot_read_another_accounts_sessions(anon: TestClient):
    """The only thing between this and showing one participant another's data."""
    register(anon, "first@example.com")
    session_id = anon.post("/sessions").json()["id"]
    anon.post(
        "/checkins",
        json={
            "taken_on": "2026-09-06",
            "instrument": "PHQ-8",
            "responses": {f"q{index}": 1 for index in range(1, 9)},
            "score": 8,
        },
    )
    anon.post("/auth/logout")
    anon.cookies.clear()

    anon.post("/auth/register", json=OTHER)

    assert anon.get("/sessions").json() == []
    assert anon.get("/checkins").json() == []
    assert anon.get(f"/sessions/{session_id}").status_code == 404
    assert anon.delete(f"/sessions/{session_id}").status_code == 404
    assert anon.get("/trends?days=30").json()["correlation"]["n"] == 0


def test_withdrawal_only_deletes_the_signed_in_accounts_data(anon: TestClient):
    register(anon, "keeper@example.com")
    anon.post("/sessions")
    anon.post("/auth/logout")
    anon.cookies.clear()

    anon.post("/auth/register", json=OTHER)
    receipt = anon.delete("/users/me/data").json()
    assert receipt["deleted_sessions"] == 0

    anon.post("/auth/logout")
    anon.cookies.clear()
    anon.post("/auth/login", json={"email": "keeper@example.com", "password": PASSWORD})
    assert len(anon.get("/sessions").json()) == 1


# ── throttling ────────────────────────────────────────────────────────


def test_repeated_failures_are_throttled(anon: TestClient):
    register(anon, "throttled@example.com")
    anon.post("/auth/logout")

    for _ in range(MAX_ATTEMPTS):
        anon.post("/auth/login", json={"email": "throttled@example.com", "password": "nope"})

    blocked = anon.post("/auth/login", json={"email": "throttled@example.com", "password": PASSWORD})
    assert blocked.status_code == 429
    assert str(COOLDOWN_SECONDS // 60) in blocked.json()["detail"] or "seconds" in blocked.json()["detail"]


def test_a_successful_login_clears_the_failure_count(anon: TestClient):
    register(anon, "recovering@example.com")
    anon.post("/auth/logout")

    for _ in range(MAX_ATTEMPTS - 1):
        anon.post("/auth/login", json={"email": "recovering@example.com", "password": "nope"})
    assert (
        anon.post("/auth/login", json={"email": "recovering@example.com", "password": PASSWORD}).status_code
        == 200
    )

    anon.post("/auth/logout")
    for _ in range(MAX_ATTEMPTS - 1):
        anon.post("/auth/login", json={"email": "recovering@example.com", "password": "nope"})
    assert (
        anon.post("/auth/login", json={"email": "recovering@example.com", "password": PASSWORD}).status_code
        == 200
    )
