"""The composition root: reads config, constructs concrete providers, and
injects them (AGENTS.md section 6). Wiring happens here and nowhere else.
"""

from dataclasses import dataclass

from sentinel.audio import AplayAudioPlayer, AudioPlayer, MockAudioPlayer
from sentinel.camera import CameraError, CameraProvider, MockCamera
from sentinel.config import Settings
from sentinel.database import (
    EventRepository,
    RecordingRepository,
    SessionRepository,
    apply_migrations,
    open_engine,
)
from sentinel.detection import (
    DetectionDebouncer,
    DetectionError,
    Detector,
    MockDetector,
)
from sentinel.events import EventBus, Notification, TimerService
from sentinel.rules import RuleEngine
from sentinel.services.auth import AuthService
from sentinel.services.detection_loop import DetectionLoop
from sentinel.services.dispatcher import EventDispatcher
from sentinel.services.recorder import Recorder
from sentinel.state import StateMachine


@dataclass
class Container:
    """Everything the API layer needs, already wired together."""

    settings: Settings
    event_repository: EventRepository
    recording_repository: RecordingRepository
    session_repository: SessionRepository
    bus: EventBus
    state_machine: StateMachine
    rule_engine: RuleEngine
    timer_service: TimerService
    audio_player: AudioPlayer
    camera_provider: CameraProvider
    detector: Detector
    detection_loop: DetectionLoop
    recorder: Recorder
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
    recording_repository = RecordingRepository(engine)
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

    detector: Detector
    if settings.detection.provider == "mock":
        detector = MockDetector()
    else:
        raise DetectionError(
            "detection.provider 'onnx' is not implemented until slice 10; "
            "set detection.provider = 'mock'"
        )

    debouncer = DetectionDebouncer(settings.detection)
    detection_loop = DetectionLoop(
        camera_provider=camera_provider,
        detector=detector,
        debouncer=debouncer,
        bus=bus,
        interval_seconds=1.0 / settings.detection.max_inference_fps,
    )

    recorder = Recorder(
        camera_provider=camera_provider,
        recording_repository=recording_repository,
        recordings_path=settings.storage.recordings_path,
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
        recorder=recorder,
        detection_loop=detection_loop,
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
        recording_repository=recording_repository,
        session_repository=session_repository,
        bus=bus,
        state_machine=state_machine,
        rule_engine=rule_engine,
        timer_service=timer_service,
        audio_player=audio_player,
        camera_provider=camera_provider,
        detector=detector,
        detection_loop=detection_loop,
        recorder=recorder,
        dispatcher=dispatcher,
        auth_service=auth_service,
    )
