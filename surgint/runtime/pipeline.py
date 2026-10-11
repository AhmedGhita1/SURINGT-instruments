from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import List, Optional, Union

import numpy as np
import torch

from surgint.model import TASKS, Detections
from surgint.model.boxes import nms
from surgint.model.decode import decode
from surgint.model.detector import Detector
from surgint.model.transform import Transform
from surgint.runtime.bytetrack import ByteTrack


@dataclass(frozen=True)
class PipelineTiming:
    """Elapsed time for one pipeline call, measured on one monotonic clock."""

    preprocess_ms: float
    inference_ms: float
    postprocess_ms: float
    tracking_ms: float
    total_ms: float


class Pipeline:
    def __init__(
        self,
        detector: Detector,
        transform: Transform,
        task: str,
        tracker: Optional[dict] = None,
        max_detections: Optional[int] = None,
        nms_iou: Optional[float] = None,
    ):

        if task not in TASKS:
            raise ValueError(f"task must be one of {TASKS}, got {task!r}")

        self.detector = detector
        self.transform = transform
        self.task = task
        self.max_detections = max_detections
        self.nms_iou = nms_iou
        self.tracker = ByteTrack(**(tracker or {})) if task == "detection-tracking" else None
        self.last_timing: Optional[PipelineTiming] = None

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: Union[str, Path],
        task: str = "detection-only",
        device: str = "cuda",
        tracker: Optional[dict] = None,
        max_detections: Optional[int] = None,
        nms_iou: Optional[float] = None,
    ) -> "Pipeline":
        detector = Detector.from_checkpoint(checkpoint).to(device)
        meta = detector.meta
        transform = Transform(meta["input_size"], meta["pad_color"], meta["rescale_factor"])
        return cls(detector, transform, task, tracker, max_detections, nms_iou)

    def predict(self, frame: np.ndarray, score_threshold: float) -> Detections:
        return self.predict_batch([frame], score_threshold)[0]

    def predict_batch(
        self,
        frames: List[np.ndarray],
        score_threshold: float,
    ) -> List[Detections]:
        """Run one model forward pass, then update tracking in frame order."""
        started_at = perf_counter()
        if not frames:
            self.last_timing = PipelineTiming(0.0, 0.0, 0.0, 0.0, 0.0)
            return []

        # the tracker needs low scoring boxes for its second pass. under tracking,
        # decode runs at low_thresh and score_threshold is unused.
        threshold = self.tracker.low_thresh if self.tracker else score_threshold

        phase_started_at = perf_counter()
        samples = [self.transform(frame) for frame in frames]
        pixel_values = torch.stack([sample["pixel_values"] for sample in samples])
        preprocess_ms = _elapsed_ms(phase_started_at)

        phase_started_at = perf_counter()
        logits, pred_boxes = self.detector.predict(pixel_values)
        inference_ms = _elapsed_ms(phase_started_at)

        phase_started_at = perf_counter()
        decoded = decode(logits, pred_boxes, threshold, self.max_detections)
        postprocess_ms = _elapsed_ms(phase_started_at)
        tracking_ms = 0.0

        results = []
        for sample, (boxes, scores, class_ids) in zip(samples, decoded):
            phase_started_at = perf_counter()
            boxes = self.transform.postprocess(boxes, sample["scale"], sample["frame_size"])

            # the detector puts more than one query on the same instrument, and each extra
            # box opens a second track on it
            if self.nms_iou is not None:
                keep = nms(boxes, scores, self.nms_iou)
                boxes, scores, class_ids = boxes[keep], scores[keep], class_ids[keep]

            detections = Detections(boxes, scores, class_ids)
            postprocess_ms += _elapsed_ms(phase_started_at)

            phase_started_at = perf_counter()
            results.append(self.tracker.update(detections) if self.tracker else detections)
            tracking_ms += _elapsed_ms(phase_started_at)

        self.last_timing = PipelineTiming(
            preprocess_ms=preprocess_ms,
            inference_ms=inference_ms,
            postprocess_ms=postprocess_ms,
            tracking_ms=tracking_ms,
            total_ms=_elapsed_ms(started_at),
        )
        return results

    def reset(self) -> None:
        """drop the tracking state. call between sequences"""
        if self.tracker is not None:
            self.tracker.reset()


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000.0
