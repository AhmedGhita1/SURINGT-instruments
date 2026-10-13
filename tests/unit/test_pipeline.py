"""
Pipeline tests
==============

tests the runtime path: a frame in, Detections out.

a stub detector stands in for the weights, so the boxes are controlled and the
coordinate round trip can be checked exactly.

coverage:
- task:       the key is validated, track_ids stay empty for detection-only
- predict:    Detections in frame pixels, aligned arrays, threshold
- checkpoint: from_checkpoint takes its geometry from the model manifest
- tracking:   track_ids under detection-tracking, None under detection-only
"""

import numpy as np
import pytest
import torch

from surgint.model import Detections
from surgint.model.transform import Transform
from surgint.runtime.bytetrack import CONFIRM_HITS
from surgint.runtime.pipeline import Pipeline

INPUT_SIZE = [320, 192]
FRAME_HEIGHT, FRAME_WIDTH = 180, 320
CLASSES = 2


class StubDetector:
    """one query per frame, at a fixed normalized box and class"""

    def __init__(self, boxes: np.ndarray, class_id: int = 0, score: float = 0.9):
        self.boxes = boxes
        self.class_id = class_id
        self.score = score

    def predict(self, pixel_values):
        assert pixel_values.dim() == 4, "the model always takes a batch"

        batch_size = len(pixel_values)
        logits = torch.full((batch_size, len(self.boxes), CLASSES), -10.0)
        logits[:, :, self.class_id] = torch.logit(torch.tensor(self.score))
        boxes = torch.tensor(self.boxes, dtype=torch.float32).unsqueeze(0)
        return logits, boxes.repeat(batch_size, 1, 1)


def blank() -> np.ndarray:
    return np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)


def test_task():
    """the key the pipeline is built with"""

    transform = Transform(INPUT_SIZE)
    detector = StubDetector(np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32))

    assert Pipeline(detector, transform, "detection-only").task == "detection-only"
    assert Pipeline(detector, transform, "detection-tracking").task == "detection-tracking"

    try:
        Pipeline(detector, transform, "segmentation")
        assert False, "should raise for an unknown task"
    except ValueError:
        pass


def test_predict():
    """a frame in, Detections out"""

    transform = Transform(INPUT_SIZE)

    # a frame box put through the transform, then handed back as the model output
    frame_box = np.array([[40.0, 60.0, 100.0, 110.0]], dtype=np.float32)
    normalized = transform(blank(), frame_box, np.array([0], dtype=np.int64))["boxes"]

    pipeline = Pipeline(StubDetector(normalized), transform, "detection-only")
    result = pipeline.predict(blank(), score_threshold=0.3)

    assert isinstance(result, Detections)
    assert len(result.boxes) == len(result.scores) == len(result.class_ids) == 1

    # the box comes back where it started, in frame pixels
    assert np.allclose(result.boxes, frame_box, atol=1e-2), f"got {result.boxes}"
    assert result.boxes.dtype == np.float32

    # detection-only leaves the tracker's field empty
    assert result.track_ids is None, "detection-only must not invent track ids"

    # the threshold filters, so nothing survives above the query's score
    assert len(pipeline.predict(blank(), score_threshold=0.99).boxes) == 0

    # an empty result keeps the shapes a consumer expects
    empty = pipeline.predict(blank(), score_threshold=0.99)
    assert empty.boxes.shape == (0, 4)
    assert empty.scores.shape == (0,) and empty.class_ids.shape == (0,)


def test_predict_records_phase_timing_without_changing_the_result():
    transform = Transform(INPUT_SIZE)
    pipeline = Pipeline(
        StubDetector(np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32)),
        transform,
        "detection-only",
    )

    result = pipeline.predict(blank(), score_threshold=0.3)
    timing = pipeline.last_timing

    assert len(result.boxes) == 1
    assert timing is not None
    assert timing.preprocess_ms >= 0.0
    assert timing.inference_ms >= 0.0
    assert timing.postprocess_ms >= 0.0
    assert timing.tracking_ms >= 0.0
    assert timing.total_ms >= timing.inference_ms


def test_empty_batch_records_zero_timing():
    pipeline = Pipeline(
        StubDetector(np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32)),
        Transform(INPUT_SIZE),
        "detection-only",
    )

    assert pipeline.predict_batch([], score_threshold=0.3) == []
    assert pipeline.last_timing is not None
    assert pipeline.last_timing.total_ms == 0.0


def test_tracking():
    """track_ids across frames, and reset between sequences"""

    transform = Transform(INPUT_SIZE)
    boxes = np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32)

    # detection-only leaves track_ids None. reset is a no-op and must not raise.
    plain = Pipeline(StubDetector(boxes), transform, "detection-only")
    assert plain.tracker is None, "detection-only must not build a tracker"
    assert plain.predict(blank(), 0.3).track_ids is None, "detection-only must not track"
    plain.reset()

    tracked = Pipeline(StubDetector(boxes), transform, "detection-tracking")

    # nothing is reported before confirmation
    for hit in range(CONFIRM_HITS - 1):
        assert len(tracked.predict(blank(), 0.3).boxes) == 0, f"reported at {hit + 1} hits"

    result = tracked.predict(blank(), 0.3)
    assert result.track_ids.tolist() == [1], f"got {result.track_ids.tolist()}"
    assert len(result.boxes) == len(result.track_ids), "the arrays must stay aligned"

    # the id holds while the instrument is present
    for _ in range(3):
        assert tracked.predict(blank(), 0.3).track_ids.tolist() == [1], "the id must not change"

    # reset clears the tracks and the id counter
    tracked.reset()
    for _ in range(CONFIRM_HITS):
        result = tracked.predict(blank(), 0.3)
    assert result.track_ids.tolist() == [1], f"expected id 1 after reset, got {result.track_ids.tolist()}"


def test_predict_batch_runs_one_forward_pass_and_tracks_in_order():
    transform = Transform(INPUT_SIZE)
    detector = StubDetector(np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32))
    pipeline = Pipeline(detector, transform, "detection-tracking")

    results = pipeline.predict_batch([blank() for _ in range(CONFIRM_HITS)], 0.0)

    assert len(results) == CONFIRM_HITS
    assert all(len(result.boxes) == 0 for result in results[:-1])
    assert results[-1].track_ids.tolist() == [1]


def test_timestamped_batch_uses_elapsed_confirmation_time():
    transform = Transform(INPUT_SIZE)
    detector = StubDetector(np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32))
    pipeline = Pipeline(detector, transform, "detection-tracking")

    fast_timestamps = [step * 0.1 for step in range(CONFIRM_HITS)]
    fast = pipeline.predict_batch(
        [blank() for _ in fast_timestamps],
        0.0,
        capture_timestamps=fast_timestamps,
    )
    assert all(len(result.boxes) == 0 for result in fast)

    later_timestamps = [step * 0.1 for step in range(CONFIRM_HITS, 9)]
    later = pipeline.predict_batch(
        [blank() for _ in later_timestamps],
        0.0,
        capture_timestamps=later_timestamps,
    )
    assert later[-1].track_ids.tolist() == [1]


def test_batch_rejects_misaligned_capture_timestamps():
    pipeline = Pipeline(
        StubDetector(np.array([[0.5, 0.5, 0.2, 0.2]], dtype=np.float32)),
        Transform(INPUT_SIZE),
        "detection-tracking",
    )

    with pytest.raises(ValueError, match="one-to-one"):
        pipeline.predict_batch([blank(), blank()], 0.0, capture_timestamps=[0.0])
