from fastapi.testclient import TestClient

from sentinel.api import create_app
from sentinel.config import Settings
from sentinel.services import build_container
from tests.conftest import TEST_PIN


def _client(settings: Settings) -> TestClient:
    container = build_container(settings)
    return TestClient(create_app(container))


def test_dashboard_page_loads(settings: Settings) -> None:
    client = _client(settings)

    response = client.get("/")

    assert response.status_code == 200
    assert "SENTINEL" in response.text


def test_status_reflects_disarmed_by_default(settings: Settings) -> None:
    client = _client(settings)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    assert response.json() == {"state": "disarmed"}


def test_arm_without_session_is_rejected(settings: Settings) -> None:
    client = _client(settings)

    response = client.post("/api/system/arm")

    assert response.status_code == 401


def test_login_with_wrong_pin_is_rejected(settings: Settings) -> None:
    client = _client(settings)

    response = client.post("/api/auth/login", json={"pin": "0000"})

    assert response.status_code == 401


def test_login_then_arm_changes_status(settings: Settings) -> None:
    client = _client(settings)

    login = client.post("/api/auth/login", json={"pin": TEST_PIN})
    assert login.status_code == 200
    assert "sentinel_session" in login.cookies

    arm = client.post("/api/system/arm")
    assert arm.status_code == 200

    status = client.get("/api/system/status")
    assert status.json() == {"state": "armed"}


def test_arm_twice_is_a_conflict_not_a_crash(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})
    client.post("/api/system/arm")

    response = client.post("/api/system/arm")

    assert response.status_code == 409


def test_disarm_wins_from_any_state(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})
    client.post("/api/system/arm")

    response = client.post("/api/system/disarm")

    assert response.status_code == 200
    assert client.get("/api/system/status").json() == {"state": "disarmed"}


def test_logout_revokes_the_session(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    arm = client.post("/api/system/arm")
    assert arm.status_code == 401


def test_lockout_after_repeated_failures(settings: Settings) -> None:
    client = _client(settings)

    for _ in range(3):  # fixture sets auth.max_attempts = 3
        client.post("/api/auth/login", json={"pin": "0000"})

    response = client.post("/api/auth/login", json={"pin": TEST_PIN})

    assert response.status_code == 423


def test_recent_events_render_after_arming(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})
    client.post("/api/system/arm")

    response = client.get("/api/events/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["type"] == "system_armed"


def test_status_partial_renders_current_state(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})
    client.post("/api/system/arm")

    response = client.get("/partials/status")

    assert response.status_code == 200
    assert "ARMED" in response.text


def test_events_partial_renders_recent_events(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})
    client.post("/api/system/arm")

    response = client.get("/partials/events")

    assert response.status_code == 200
    assert "system_armed" in response.text


def test_docs_are_disabled_to_avoid_a_cdn_fetch(settings: Settings) -> None:
    client = _client(settings)

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_lock_screen_shows_disarmed_by_default(settings: Settings) -> None:
    client = _client(settings)

    response = client.get("/")

    assert response.status_code == 200
    assert "DISARMED" in response.text
    assert "does not disarm the system" in response.text.lower()
    assert 'id="console-gate"' in response.text
    assert "Access console" in response.text


def test_lock_status_partial_reflects_armed_state(settings: Settings) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})
    client.post("/api/system/arm")

    response = client.get("/partials/lock-status")

    assert response.status_code == 200
    assert "ARMED" in response.text
    assert 'data-armed="true"' in response.text
    assert "REC" in response.text


def test_console_page_requires_a_session(settings: Settings) -> None:
    client = _client(settings)

    response = client.get("/console", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_console_page_loads_after_login_and_links_back_to_lock_screen(
    settings: Settings,
) -> None:
    client = _client(settings)
    client.post("/api/auth/login", json={"pin": TEST_PIN})

    response = client.get("/console")

    assert response.status_code == 200
    assert "CONSOLE" in response.text
    assert 'href="/"' in response.text


def test_state_detail_partial_describes_current_state(settings: Settings) -> None:
    client = _client(settings)

    response = client.get("/partials/state-detail")

    assert response.status_code == 200
    assert "Monitoring is off" in response.text
