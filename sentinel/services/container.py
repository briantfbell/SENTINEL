"""The composition root: reads config, constructs concrete providers, and
injects them (AGENTS.md section 6). Wiring happens here and nowhere else.
"""

from dataclasses import dataclass

from sentinel.audio import AplayAudioPlayer, AudioPlayer, MockAudioPlayer
from sentinel.camera import CameraError, CameraProvider, MockCamera
from sentinel.config import Settings
from sentinel.database import (
    EventRepository,
    SessionRepository,
    apply_migrations,
    open_engine,
)
from sentinel.events import EventBus, Notification, TimerService
from sentinel.rules import RuleEngine
from sentinel.services.auth import AuthService
from sentinel.services.dispatcher import EventDispatcher
from sentinel.state import StateMachine


@dataclass
class Container:
    """Everything the API layer needs, already wired together."""

    settings: Settings
    event_repository: EventRepository
    session_repository: SessionRepository
    bus: EventBus
    state_machine: StateMachine
    rule_engine: RuleEngine
    timer_service: TimerService
    audio_player: AudioPlayer
    camera_provider: CameraProvider
    dispatcher: EventDispatcher
    auth_service: AuthService


def build_container(settings: Settings) -> Container:
    """Construct and wire every component from validated settings.

    Mock vs. real providers (camera, detection, audio) are selected here
    too once those layers exist; for now this wires the parts slices 0-5
    have built.
    """
    engine = open_engine(settings.database.path)
    apply_migrations(engine)

    event_repository = EventRepository(engine)
    session_repository = SessionRepository(engine)

    bus = EventBus()
    state_machine = StateMachine()
    rule_engine = RuleEngine()
    timer_service = TimerService(bus)

    audio_player: AudioPlayer
    if settings.audio.provider == "mock":
        audio_player = MockAudioPlayer()
    else:
        audio_player = AplayAudioPlayer(
            device=settings.audio.device, mixer_control=settings.audio.mixer_control
        )

    camera_provider: CameraProvider
    if settings.camera.provider == "mock":
        camera_provider = MockCamera(stills_dir=settings.camera.mock_stills_dir)
    else:
        raise CameraError(
            "camera.provider 'rtsp' is not implemented until slice 9; "
            "set camera.provider = 'mock'"
        )

    dispatcher = EventDispatcher(
        state_machine=state_machine,
        rule_engine=rule_engine,
        event_repository=event_repository,
        timer_service=timer_service,
        state_settings=settings.state,
        bus=bus,
        audio_player=audio_player,
        audio_settings=settings.audio,
    )

    async def _on_notification(notification: Notification) -> None:
        # Bus subscribers are fire-and-forget (Handler returns None); the
        # DispatchResult is for direct callers of on_notification, e.g. tests.
        await dispatcher.on_notification(notification)

    bus.subscribe(_on_notification)

    auth_service = AuthService(
        session_repository=session_repository,
        pin_hash=settings.auth.pin_hash,
        session_ttl_seconds=settings.auth.session_ttl_seconds,
        max_attempts=settings.auth.max_attempts,
        lockout_seconds=settings.auth.lockout_seconds,
    )

    return Container(
        settings=settings,
        event_repository=event_repository,
        session_repository=session_repository,
        bus=bus,
        state_machine=state_machine,
        rule_engine=rule_engine,
        timer_service=timer_service,
        audio_player=audio_player,
        camera_provider=camera_provider,
        dispatcher=dispatcher,
        auth_service=auth_service,
    )
