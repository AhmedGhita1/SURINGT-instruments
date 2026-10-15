from dataclasses import dataclass
from enum import Enum
from math import isfinite
from uuid import UUID

from surgint.decision import Decision, ItemContext
from surgint.model import Detections
from surgint.runtime.decision_support import InventoryDecisionSupport
from surgint.runtime.inventory import Inventory, InventoryItem
from surgint.runtime.temporal import FrameIdentity


ROBOT_CONTRACT_VERSION = "1.0"
MAX_ANALYSIS_LAG_SECONDS = 0.4
IMAGE_TIMEOUT_SECONDS = 1.0


class RobotRunState(str, Enum):
    READY = "ready"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


class RobotTimingCondition(str, Enum):
    WAITING_FOR_IMAGE = "waiting-for-image"
    CURRENT = "current"
    ANALYSIS_DELAYED = "analysis-delayed"
    IMAGE_STREAM_STOPPED = "image-stream-stopped"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class RobotItemResult:
    """One immutable item and handling result, frozen at first confirmation."""

    run_id: UUID
    item_id: int
    class_id: int
    label: str
    confidence: float
    resolution_sequence: int
    source_id: str
    source_sequence: int
    captured_at: float
    decision: Decision
    schema_version: str = ROBOT_CONTRACT_VERSION

    @property
    def handling_outcome(self) -> str:
        return (
            "Recommendation"
            if self.decision.outcome == "recommendation"
            else "Needs review"
        )

    @property
    def action(self) -> str | None:
        return self.decision.action

    @property
    def reason(self) -> str:
        return self.decision.reason


@dataclass(frozen=True)
class RobotInventoryEntry:
    """One append-only robot inventory entry and its associated outcome."""

    run_id: UUID
    item_id: int
    class_id: int
    label: str
    resolution_sequence: int
    captured_at: float
    class_count: int
    handling_outcome: str
    action: str | None
    reason: str
    schema_version: str = ROBOT_CONTRACT_VERSION


@dataclass(frozen=True)
class RobotRunStatus:
    """Immutable snapshot of one robot run's workflow and timing condition."""

    run_id: UUID
    state: RobotRunState
    timing_condition: RobotTimingCondition
    frame_count: int
    result_count: int
    latest_received_source_at: float | None
    latest_analyzed_source_at: float | None
    failure: str | None
    schema_version: str = ROBOT_CONTRACT_VERSION


@dataclass(frozen=True)
class RobotRunSummary:
    """Immutable terminal inventory and decision summary for one robot run."""

    run_id: UUID
    state: RobotRunState
    started_at: float
    ended_at: float
    frame_count: int
    results: tuple[RobotItemResult, ...]
    inventory: tuple[RobotInventoryEntry, ...]
    failure: str | None
    schema_version: str = ROBOT_CONTRACT_VERSION


class RobotRunCoordinator:
    """Coordinate incremental robot inventory and decisions for one isolated run."""

    def __init__(
        self,
        run_id: UUID,
        support: InventoryDecisionSupport,
        context: ItemContext,
    ):
        if not isinstance(run_id, UUID):
            raise TypeError("run_id must be a UUID")
        if not isinstance(support, InventoryDecisionSupport):
            raise TypeError("support must be an InventoryDecisionSupport")
        if not isinstance(context, ItemContext):
            raise TypeError("context must be an ItemContext")

        self.run_id = run_id
        self._support = support
        self._context = context
        self._inventory = Inventory()
        self._state = RobotRunState.READY
        self._started_at: float | None = None
        self._ended_at: float | None = None
        self._last_received_at: float | None = None
        self._latest_received_source_at: float | None = None
        self._latest_analyzed_source_at: float | None = None
        self._pending_frame: FrameIdentity | None = None
        self._publications: tuple[
            tuple[RobotItemResult, RobotInventoryEntry], ...
        ] = ()
        self._resolved_item_ids: set[int] = set()
        self._failure: str | None = None
        self._summary: RobotRunSummary | None = None

    @property
    def results(self) -> tuple[RobotItemResult, ...]:
        return tuple(result for result, _entry in self._publications)

    @property
    def inventory(self) -> tuple[RobotInventoryEntry, ...]:
        return tuple(entry for _result, entry in self._publications)

    @property
    def summary(self) -> RobotRunSummary:
        if self._summary is None:
            raise RuntimeError("run has not stopped or failed")
        return self._summary

    def start(self, started_at: float) -> RobotRunStatus:
        """Move a ready coordinator to active after startup validation succeeds."""

        if self._state is not RobotRunState.READY:
            raise RuntimeError("run has already started")
        self._started_at = _time(started_at, "started_at")
        self._state = RobotRunState.ACTIVE
        return self.status(started_at)

    def record_received(
        self,
        frame: FrameIdentity,
        received_at: float,
    ) -> None:
        """Record one accepted image before its detector request begins."""

        self._require_running()
        if not isinstance(frame, FrameIdentity):
            raise TypeError("frame must be a FrameIdentity")
        received_at = _time(received_at, "received_at")
        if self._started_at is None or received_at < self._started_at:
            raise ValueError("received_at cannot precede the run start")
        if self._last_received_at is not None and received_at < self._last_received_at:
            raise ValueError("received_at cannot move backwards")
        if self._pending_frame is not None:
            raise RuntimeError("run is already processing an image")

        self._pending_frame = frame
        self._last_received_at = received_at
        self._latest_received_source_at = frame.captured_at

    def resolve_frame(
        self,
        frame: FrameIdentity,
        detections: Detections,
        completed_at: float,
    ) -> tuple[tuple[RobotItemResult, RobotInventoryEntry], ...]:
        """Resolve newly confirmed tracks and publish each item and entry together."""

        self._require_running()
        if frame != self._pending_frame:
            raise ValueError("resolved frame does not match the accepted image")
        if not isinstance(detections, Detections):
            raise TypeError("detections must be Detections")
        if detections.track_ids is None:
            raise ValueError("robot resolution requires confirmed tracked detections")
        completed_at = _time(completed_at, "completed_at")
        if self._last_received_at is None or completed_at < self._last_received_at:
            raise ValueError("completed_at cannot precede image receipt")

        new_detections = sorted(
            (
                (int(track_id), int(class_id), float(score))
                for track_id, class_id, score in zip(
                    detections.track_ids,
                    detections.class_ids,
                    detections.scores,
                )
                if int(track_id) not in self._resolved_item_ids
            ),
            key=lambda detection: detection[0],
        )
        counts = {entry.class_id: entry.class_count for entry in self.inventory}
        next_sequence = len(self._publications) + 1
        staged: list[tuple[RobotItemResult, RobotInventoryEntry]] = []

        try:
            for offset, (track_id, class_id, score) in enumerate(new_detections):
                decision = self._support.resolve_item(
                    InventoryItem(
                        track_id=track_id,
                        class_id=class_id,
                        first_seen=self._inventory.frame,
                        last_seen=self._inventory.frame,
                        frames=1,
                        score=score,
                    ),
                    self._context,
                )
                sequence = next_sequence + offset
                result = RobotItemResult(
                    run_id=self.run_id,
                    item_id=track_id,
                    class_id=class_id,
                    label=decision.label,
                    confidence=score,
                    resolution_sequence=sequence,
                    source_id=frame.source_id,
                    source_sequence=frame.sequence,
                    captured_at=frame.captured_at,
                    decision=decision,
                )
                class_count = counts.get(class_id, 0) + 1
                counts[class_id] = class_count
                entry = RobotInventoryEntry(
                    run_id=self.run_id,
                    item_id=track_id,
                    class_id=class_id,
                    label=decision.label,
                    resolution_sequence=sequence,
                    captured_at=frame.captured_at,
                    class_count=class_count,
                    handling_outcome=result.handling_outcome,
                    action=result.action,
                    reason=result.reason,
                )
                staged.append((result, entry))
        except Exception as error:
            self.fail(f"item resolution failed: {error}", completed_at)
            raise

        self._inventory.update(detections)
        publications = tuple(staged)
        self._publications += publications
        self._resolved_item_ids.update(result.item_id for result, _entry in publications)
        self._latest_analyzed_source_at = frame.captured_at
        self._pending_frame = None
        return publications

    def status(self, now: float) -> RobotRunStatus:
        """Return current state, deriving degradation from the declared time limits."""

        now = _time(now, "now")
        state = self._state
        if state is RobotRunState.READY:
            timing = RobotTimingCondition.WAITING_FOR_IMAGE
        elif state in (RobotRunState.STOPPED, RobotRunState.FAILED):
            timing = RobotTimingCondition.TERMINAL
        else:
            if self._started_at is None or now < self._started_at:
                raise ValueError("now cannot precede the run start")
            last_arrival = self._last_received_at or self._started_at
            if now - last_arrival >= IMAGE_TIMEOUT_SECONDS:
                state = RobotRunState.DEGRADED
                timing = RobotTimingCondition.IMAGE_STREAM_STOPPED
            elif (
                self._latest_received_source_at is not None
                and self._latest_analyzed_source_at is not None
                and self._latest_received_source_at - self._latest_analyzed_source_at
                > MAX_ANALYSIS_LAG_SECONDS
            ):
                state = RobotRunState.DEGRADED
                timing = RobotTimingCondition.ANALYSIS_DELAYED
            elif self._latest_analyzed_source_at is None:
                timing = RobotTimingCondition.WAITING_FOR_IMAGE
            else:
                timing = RobotTimingCondition.CURRENT

        return RobotRunStatus(
            run_id=self.run_id,
            state=state,
            timing_condition=timing,
            frame_count=self._inventory.frame,
            result_count=len(self._publications),
            latest_received_source_at=self._latest_received_source_at,
            latest_analyzed_source_at=self._latest_analyzed_source_at,
            failure=self._failure,
        )

    def stop(self, ended_at: float) -> RobotRunSummary:
        """Stop the run and freeze its final inventory and decisions."""

        self._require_running()
        if self._pending_frame is not None:
            raise RuntimeError("cannot stop while an image is processing")
        self._ended_at = self._terminal_time(ended_at)
        self._state = RobotRunState.STOPPED
        self._summary = self._build_summary()
        return self._summary

    def fail(self, detail: str, ended_at: float) -> RobotRunSummary:
        """Move the run to terminal failure and prevent further resolutions."""

        self._require_running()
        if not isinstance(detail, str) or not detail.strip():
            raise ValueError("failure detail must be a non-empty string")
        self._ended_at = self._terminal_time(ended_at)
        self._failure = detail
        self._pending_frame = None
        self._state = RobotRunState.FAILED
        self._summary = self._build_summary()
        return self._summary

    def _terminal_time(self, ended_at: float) -> float:
        ended_at = _time(ended_at, "ended_at")
        if self._started_at is None or ended_at < self._started_at:
            raise ValueError("ended_at cannot precede the run start")
        return ended_at

    def _build_summary(self) -> RobotRunSummary:
        if self._started_at is None or self._ended_at is None:
            raise RuntimeError("terminal run timestamps are incomplete")
        return RobotRunSummary(
            run_id=self.run_id,
            state=self._state,
            started_at=self._started_at,
            ended_at=self._ended_at,
            frame_count=self._inventory.frame,
            results=self.results,
            inventory=self.inventory,
            failure=self._failure,
        )

    def _require_running(self) -> None:
        if self._state is not RobotRunState.ACTIVE:
            raise RuntimeError(f"run is not active: {self._state.value}")


def _time(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite non-negative number")
    value = float(value)
    if not isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return value
