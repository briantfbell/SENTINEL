import asyncio

from sentinel.config import Settings
from sentinel.models import EventType, SystemState
from sentinel.services import build_container
from tests.conftest import TEST_PIN


def test_build_container_wires_publish_to_state_and_log(settings: Settings) -> None:
    container = build_container(settings)

    asyncio.run(container.bus.publish(EventType.SYSTEM_ARMED, source="test"))

    assert container.state_machine.state == SystemState.ARMED
    assert len(container.event_repository.query()) == 1


def test_build_container_wires_auth(settings: Settings) -> None:
    container = build_container(settings)

    token = container.auth_service.login(TEST_PIN, "127.0.0.1")

    assert container.auth_service.validate_session(token) is True


def test_build_container_wires_mock_camera_by_default(settings: Settings) -> None:
    container = build_container(settings)

    assert container.camera_provider.get_snapshot().startswith(b"\xff\xd8")
