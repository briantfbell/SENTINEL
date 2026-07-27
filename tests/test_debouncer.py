from datetime import UTC, datetime, timedelta

from sentinel.config import DetectionSettings
from sentinel.detection import Detection, DetectionDebouncer
from sentinel.models import EventType

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)
HIT = Detection(confidence=0.9, box_area_ratio=0.5)
NO_HIT: list[Detection] = []


def _debouncer(current: dict[str, datetime]) -> DetectionDebouncer:
    settings = DetectionSettings(
        confidence_threshold=0.55,
        consecutive_frames=3,
        absence_seconds=8.0,
        min_box_area_ratio=0.01,
    )
    return DetectionDebouncer(settings, clock=lambda: current["now"])


def test_fires_person_detected_after_consecutive_frames() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)

    results = [debouncer.process([HIT]) for _ in range(3)]

    assert results == [None, None, EventType.PERSON_DETECTED]


def test_does_not_fire_at_one_frame_short() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)

    results = [debouncer.process([HIT]) for _ in range(2)]

    assert results == [None, None]


def test_only_fires_once_while_present() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)
    for _ in range(3):
        debouncer.process([HIT])

    result = debouncer.process([HIT])

    assert result is None


def test_ignores_low_confidence() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)
    low_confidence = Detection(confidence=0.1, box_area_ratio=0.5)

    results = [debouncer.process([low_confidence]) for _ in range(5)]

    assert all(result is None for result in results)


def test_ignores_undersized_boxes() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)
    tiny_box = Detection(confidence=0.9, box_area_ratio=0.001)

    results = [debouncer.process([tiny_box]) for _ in range(5)]

    assert all(result is None for result in results)


def test_non_qualifying_frame_resets_the_consecutive_count() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)
    debouncer.process([HIT])
    debouncer.process([HIT])

    debouncer.process(NO_HIT)  # resets the streak
    results = [debouncer.process([HIT]) for _ in range(2)]

    assert results == [None, None]  # would have fired without the reset


def test_emits_person_gone_after_absence_window() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)
    for _ in range(3):
        debouncer.process([HIT])

    current["now"] = NOW + timedelta(seconds=8)
    result = debouncer.process(NO_HIT)

    assert result == EventType.PERSON_GONE


def test_does_not_emit_person_gone_before_absence_window() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)
    for _ in range(3):
        debouncer.process([HIT])

    current["now"] = NOW + timedelta(seconds=7)
    result = debouncer.process(NO_HIT)

    assert result is None


def test_does_not_emit_person_gone_if_never_present() -> None:
    current = {"now": NOW}
    debouncer = _debouncer(current)

    current["now"] = NOW + timedelta(seconds=100)
    result = debouncer.process(NO_HIT)

    assert result is None
