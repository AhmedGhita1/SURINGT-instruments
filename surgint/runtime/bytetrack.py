from collections import Counter
from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt

import numpy as np
from scipy.optimize import linear_sum_assignment

from surgint.model import Detections
from surgint.model.boxes import iou_matrix
from surgint.runtime.kalman import MEASUREMENT_DIM, KalmanFilter, to_box, to_measurement

# detections required before a track is confirmed
CONFIRM_HITS = 5
CONFIRMATION_SECONDS = 0.8
NOMINAL_INTERVAL_SECONDS = 0.2
DISPLAY_PREDICTION_MAX_AGE_SECONDS = 0.4

# threshold for the second association pass. stricter than match_thresh because low
# scoring boxes are unreliable.
RESCUE_MATCH_THRESH = 0.5


class TrackState(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    LOST = "lost"


class PredictionValidity(str, Enum):
    VALID = "valid"
    TOO_OLD = "too-old"
    NON_FINITE = "non-finite"
    INVALID_GEOMETRY = "invalid-geometry"


@dataclass(frozen=True)
class DisplayPrediction:
    """A read-only projection for display that is not tracker evidence."""

    track_id: int
    box: np.ndarray
    score: float
    class_id: int
    track_state: TrackState
    state_timestamp: float
    prediction_age: float
    position_uncertainty: float
    validity: PredictionValidity

    def __post_init__(self) -> None:
        self.box.setflags(write=False)

    @property
    def valid(self) -> bool:
        return self.validity is PredictionValidity.VALID


class Track:
    """holds one track id, Kalman box estimate, class votes, hit count and state."""

    def __init__(
        self,
        track_id: int,
        box: np.ndarray,
        score: float,
        class_id: int,
        kalman: KalmanFilter,
        captured_at: float = 0.0,
        confirm_after_seconds: float = CONFIRMATION_SECONDS,
        nominal_interval_seconds: float | None = None,
    ):
        if nominal_interval_seconds is None:
            nominal_interval_seconds = kalman.reference_interval_seconds
        if not isfinite(captured_at) or captured_at < 0.0:
            raise ValueError("captured_at must be finite and non-negative")
        if not isfinite(confirm_after_seconds) or confirm_after_seconds < 0.0:
            raise ValueError("confirm_after_seconds must be finite and non-negative")
        if not isfinite(nominal_interval_seconds) or nominal_interval_seconds <= 0.0:
            raise ValueError("nominal_interval_seconds must be finite and positive")
        self.track_id = track_id
        self.latest_score = score
        self.kalman = kalman
        self.mean, self.covariance = kalman.initiate(to_measurement(box))
        self.state_timestamp = float(captured_at)
        self.first_observed_at = float(captured_at)
        self.last_observed_at = float(captured_at)
        self.confirm_after_seconds = confirm_after_seconds
        self.nominal_interval_seconds = nominal_interval_seconds

        self.votes = Counter([class_id])
        self.class_scores = {class_id: score}
        self.observation_timestamps = [float(captured_at)]
        self.hits = 1
        self.time_since_update = 0
        self.state = TrackState.TENTATIVE
        self.was_confirmed = False

    @property
    def box(self) -> np.ndarray:
        """the Kalman estimate as xyxy."""
        return to_box(self.mean[:MEASUREMENT_DIM])

    @property
    def class_id(self) -> int:
        """the most voted class over the track's matched detections."""
        return self.votes.most_common(1)[0][0]

    @property
    def score(self) -> float:
        """the best detector confidence associated with the majority class."""
        return self.class_scores[self.class_id]

    def predict(self, captured_at: float | None = None) -> None:
        """Advance the estimate to a later source timestamp."""
        captured_at = (
            self.state_timestamp + self.nominal_interval_seconds
            if captured_at is None
            else float(captured_at)
        )
        if not isfinite(captured_at) or captured_at <= self.state_timestamp:
            raise ValueError("prediction timestamp must be finite and advance source time")
        elapsed = captured_at - self.state_timestamp
        self.mean, self.covariance = self.kalman.predict(
            self.mean,
            self.covariance,
            elapsed_seconds=elapsed,
        )
        self.state_timestamp = captured_at
        self.time_since_update += 1

    def update(
        self,
        box: np.ndarray,
        score: float,
        class_id: int,
        captured_at: float | None = None,
    ) -> None:
        """correct the estimate with a matched box, add its class vote, count the hit."""
        if captured_at is None:
            captured_at = (
                self.state_timestamp
                if self.time_since_update
                else self.state_timestamp + self.nominal_interval_seconds
            )
        captured_at = float(captured_at)
        if not isfinite(captured_at) or captured_at < self.state_timestamp:
            raise ValueError("observation timestamp cannot precede track state")
        if captured_at > self.state_timestamp:
            self.predict(captured_at)

        self.mean, self.covariance = self.kalman.update(
            self.mean, self.covariance, to_measurement(box)
        )
        self.state_timestamp = captured_at
        self.last_observed_at = captured_at
        self.latest_score = score
        self.votes[class_id] += 1
        self.class_scores[class_id] = max(self.class_scores.get(class_id, score), score)
        self.observation_timestamps.append(captured_at)
        self.hits += 1
        self.time_since_update = 0

        observed_seconds = captured_at - self.first_observed_at
        if self.hits >= CONFIRM_HITS and observed_seconds + 1e-12 >= self.confirm_after_seconds:
            self.state = TrackState.CONFIRMED
            self.was_confirmed = True
        else:
            self.state = TrackState.TENTATIVE

    def mark_lost(self) -> None:
        """set the state to lost."""
        self.state = TrackState.LOST

    def display_prediction(
        self,
        displayed_at: float,
        max_age_seconds: float,
    ) -> DisplayPrediction:
        """Project to display time without changing filter or observation evidence."""
        if not isfinite(displayed_at) or displayed_at < self.state_timestamp:
            raise ValueError("display timestamp must be finite and not precede tracker state")
        mean, covariance = self.kalman.predict(
            self.mean,
            self.covariance,
            elapsed_seconds=displayed_at - self.state_timestamp,
        )
        box = np.asarray(to_box(mean[:MEASUREMENT_DIM]), dtype=np.float32)
        age = displayed_at - self.last_observed_at
        position_variances = np.diag(covariance)[[0, 1, 3]]
        uncertainty = float(sqrt(max(0.0, float(position_variances.max()))))

        if not np.isfinite(box).all() or not isfinite(uncertainty):
            validity = PredictionValidity.NON_FINITE
        elif box[2] <= box[0] or box[3] <= box[1]:
            validity = PredictionValidity.INVALID_GEOMETRY
        elif age > max_age_seconds:
            validity = PredictionValidity.TOO_OLD
        else:
            validity = PredictionValidity.VALID

        return DisplayPrediction(
            track_id=self.track_id,
            box=box,
            score=self.score,
            class_id=self.class_id,
            track_state=self.state,
            state_timestamp=self.last_observed_at,
            prediction_age=age,
            position_uncertainty=uncertainty,
            validity=validity,
        )


def iou_distance(tracks: list[Track], boxes: np.ndarray) -> np.ndarray:
    """1 - IoU between every track estimate and every box."""
    # distance is measured from the filter estimate, already advanced by predict()
    estimates = np.array([track.box for track in tracks], dtype=float).reshape(-1, 4)
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    return 1.0 - iou_matrix(estimates, boxes)


def associate(cost: np.ndarray, threshold: float) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """
    minimum cost assignment of tracks to detections.

    returns the matched (track, detection) pairs, the unmatched track rows and the
    unmatched detection columns. pairs costing more than threshold are rejected.
    """
    tracks, detections = cost.shape
    if not tracks or not detections:
        return [], list(range(tracks)), list(range(detections))

    matches = []
    for track, detection in zip(*linear_sum_assignment(cost)):
        # linear_sum_assignment pairs everything it can. the threshold drops pairs
        # that are too far apart.
        if cost[track, detection] <= threshold:
            matches.append((int(track), int(detection)))

    matched_tracks = {track for track, _ in matches}
    matched_detections = {detection for _, detection in matches}
    return (
        matches,
        [track for track in range(tracks) if track not in matched_tracks],
        [detection for detection in range(detections) if detection not in matched_detections],
    )


class ByteTrack:
    """
    two pass association of detections to tracks.

    boxes above high_thresh drive the first pass and open new tracks. boxes below it
    drive the second pass, which only continues confirmed tracks. matching ignores
    class; each track votes its own.
    """

    def __init__(
        self,
        high_thresh: float = 0.5,
        low_thresh: float = 0.1,
        match_thresh: float = 0.8,
        track_buffer: int = 30,
        min_box_area: float = 0.0,
        output_thresh: float = 0.0,
        nominal_interval_seconds: float = NOMINAL_INTERVAL_SECONDS,
        confirmation_seconds: float = CONFIRMATION_SECONDS,
        lost_timeout_seconds: float | None = None,
        display_prediction_max_age_seconds: float = DISPLAY_PREDICTION_MAX_AGE_SECONDS,
    ):
        if not isinstance(track_buffer, int) or isinstance(track_buffer, bool) or track_buffer < 0:
            raise ValueError("track_buffer must be a non-negative integer")
        if not isfinite(nominal_interval_seconds) or nominal_interval_seconds <= 0.0:
            raise ValueError("nominal_interval_seconds must be finite and positive")
        if not isfinite(confirmation_seconds) or confirmation_seconds < 0.0:
            raise ValueError("confirmation_seconds must be finite and non-negative")
        if lost_timeout_seconds is None:
            lost_timeout_seconds = track_buffer * NOMINAL_INTERVAL_SECONDS
        if not isfinite(lost_timeout_seconds) or lost_timeout_seconds < 0.0:
            raise ValueError("lost_timeout_seconds must be finite and non-negative")
        if (
            not isfinite(display_prediction_max_age_seconds)
            or display_prediction_max_age_seconds < 0.0
        ):
            raise ValueError("display_prediction_max_age_seconds must be finite and non-negative")
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.track_buffer = track_buffer
        self.min_box_area = min_box_area
        self.output_thresh = output_thresh
        self.nominal_interval_seconds = nominal_interval_seconds
        self.confirmation_seconds = confirmation_seconds
        self.lost_timeout_seconds = lost_timeout_seconds
        self.display_prediction_max_age_seconds = display_prediction_max_age_seconds

        self.kalman = KalmanFilter(reference_interval_seconds=nominal_interval_seconds)
        self.tracks: list[Track] = []
        self.next_id = 1
        self.latest_timestamp: float | None = None

    def update(self, detections: Detections, captured_at: float | None = None) -> Detections:
        """
        track one frame of detections.

        returns the confirmed tracks updated this frame.
        """
        captured_at = self._next_timestamp(captured_at)
        for track in self.tracks:
            track.predict(captured_at)

        boxes, scores, class_ids = self._usable(detections)
        high = np.flatnonzero(scores >= self.high_thresh)
        low = np.flatnonzero(scores < self.high_thresh)

        # first pass runs against every track, lost ones included. a returning
        # instrument keeps its id.
        pool = list(self.tracks)
        matched, missed, unclaimed = associate(iou_distance(pool, boxes[high]), self.match_thresh)
        for track, detection in matched:
            index = high[detection]
            pool[track].update(boxes[index], scores[index], class_ids[index], captured_at)

        # second pass runs only against unmatched confirmed tracks, using low scoring
        # boxes. a tentative track promoted on low scores, or a lost one revived by
        # them, becomes a false positive that never retires.
        rescue = [pool[track] for track in missed if pool[track].state is TrackState.CONFIRMED]
        matched, missed, _ = associate(iou_distance(rescue, boxes[low]), RESCUE_MATCH_THRESH)
        for track, detection in matched:
            index = low[detection]
            rescue[track].update(boxes[index], scores[index], class_ids[index], captured_at)

        for track in missed:
            rescue[track].mark_lost()

        # unmatched high scoring boxes open new tracks
        for detection in unclaimed:
            index = high[detection]
            self.tracks.append(
                Track(
                    self.next_id,
                    boxes[index],
                    scores[index],
                    class_ids[index],
                    self.kalman,
                    captured_at=captured_at,
                    confirm_after_seconds=self.confirmation_seconds,
                    nominal_interval_seconds=self.nominal_interval_seconds,
                )
            )
            self.next_id += 1

        self.tracks = [track for track in self.tracks if self._alive(track, captured_at)]
        self.latest_timestamp = captured_at
        return self._detections()

    def display_predictions(self, displayed_at: float) -> tuple[DisplayPrediction, ...]:
        """Return non-mutating projections for tracks that have been confirmed."""
        if self.latest_timestamp is None:
            return ()
        displayed_at = float(displayed_at)
        if not isfinite(displayed_at) or displayed_at < self.latest_timestamp:
            raise ValueError("display timestamp must be finite and not precede latest source time")
        return tuple(
            track.display_prediction(displayed_at, self.display_prediction_max_age_seconds)
            for track in self.tracks
            if track.was_confirmed
        )

    def reset(self) -> None:
        """drop every track and reset the id counter; call between sequences or ids leak across them"""
        self.tracks = []
        self.next_id = 1
        self.latest_timestamp = None

    def _next_timestamp(self, captured_at: float | None) -> float:
        if captured_at is None:
            return (
                0.0
                if self.latest_timestamp is None
                else self.latest_timestamp + self.nominal_interval_seconds
            )
        captured_at = float(captured_at)
        if not isfinite(captured_at) or captured_at < 0.0:
            raise ValueError("captured_at must be finite and non-negative")
        if self.latest_timestamp is not None and captured_at <= self.latest_timestamp:
            raise ValueError("captured_at must strictly advance source time")
        return captured_at

    def _usable(self, detections: Detections) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """drop boxes that are too weak or too small."""
        boxes = np.asarray(detections.boxes, dtype=float).reshape(-1, 4)
        scores = np.asarray(detections.scores, dtype=float).reshape(-1)
        class_ids = np.asarray(detections.class_ids, dtype=np.int64).reshape(-1)

        widths, heights = boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1]
        keep = (
            (widths > 0)
            & (heights > 0)
            & (widths * heights >= self.min_box_area)
            & (scores >= self.low_thresh)
        )
        return boxes[keep], scores[keep], class_ids[keep]

    def _alive(self, track: Track, captured_at: float) -> bool:
        """whether the track is kept for the next frame."""
        # tentative tracks are dropped on the first miss
        if track.state is TrackState.TENTATIVE:
            return track.time_since_update == 0
        return captured_at - track.last_observed_at <= self.lost_timeout_seconds + 1e-12

    def _detections(self) -> Detections:
        """the confirmed tracks matched this frame whose score clears output_thresh."""
        visible = [
            track
            for track in self.tracks
            if track.state is TrackState.CONFIRMED
            and track.time_since_update == 0
            and track.latest_score >= self.output_thresh
        ]
        return Detections(
            np.array([track.box for track in visible], dtype=np.float32).reshape(-1, 4),
            np.array([track.score for track in visible], dtype=np.float32),
            np.array([track.class_id for track in visible], dtype=np.int64),
            np.array([track.track_id for track in visible], dtype=np.int64),
        )
