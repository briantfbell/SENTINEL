from sentinel.detection import Detection, MockDetector


def test_default_script_is_always_empty() -> None:
    detector = MockDetector()

    results = [detector.detect(b"frame") for _ in range(5)]

    assert all(result == [] for result in results)


def test_replays_script_in_order() -> None:
    hit = [Detection(confidence=0.9, box_area_ratio=0.5)]
    detector = MockDetector([[], hit, []])

    results = [detector.detect(b"frame") for _ in range(3)]

    assert results == [[], hit, []]


def test_holds_on_the_last_frame_once_exhausted() -> None:
    hit = [Detection(confidence=0.9, box_area_ratio=0.5)]
    detector = MockDetector([[], hit])

    results = [detector.detect(b"frame") for _ in range(5)]

    assert results == [[], hit, hit, hit, hit]
