from dataclasses import dataclass, field
from threading import Lock
from uuid import UUID

from surgint.decision import ItemContext
from surgint.model.detector import Detector
from surgint.model.transform import Transform
from surgint.runtime.decision_support import InventoryDecisionSupport
from surgint.runtime.pipeline import Pipeline
from surgint.runtime.robot import RobotRunCoordinator
from surgint.runtime.temporal import (
    FrameDimensionError,
    FrameIdentity,
    FrameOrderError,
    SourceIdentityError,
)


@dataclass
class ActiveRobotRun:
    """API-owned processing and temporal state for one robot run."""

    pipeline: Pipeline
    coordinator: RobotRunCoordinator
    lock: Lock = field(default_factory=Lock, repr=False)
    source_id: str | None = None
    last_sequence: int | None = None
    last_captured_at: float | None = None

    def resolve_frame_identity(
        self,
        identity: FrameIdentity,
        source_width: int,
        source_height: int,
    ) -> FrameIdentity:
        """Apply the shared temporal frame contract to the robot source."""

        if identity.source_size != (source_width, source_height):
            raise FrameDimensionError(
                "declared source dimensions "
                f"{identity.source_width}x{identity.source_height} do not match decoded frame "
                f"{source_width}x{source_height}"
            )
        if self.source_id is not None and identity.source_id != self.source_id:
            raise SourceIdentityError(
                f"run source is {self.source_id!r}, not {identity.source_id!r}"
            )
        if self.last_sequence is not None and identity.sequence <= self.last_sequence:
            raise FrameOrderError(
                f"sequence must be greater than {self.last_sequence}, got {identity.sequence}"
            )
        if self.last_captured_at is not None and identity.captured_at <= self.last_captured_at:
            raise FrameOrderError(
                "captured_at must strictly advance source time; "
                f"previous={self.last_captured_at}, got={identity.captured_at}"
            )
        return identity

    def record_frame_identity(self, identity: FrameIdentity) -> None:
        self.source_id = identity.source_id
        self.last_sequence = identity.sequence
        self.last_captured_at = identity.captured_at


class RobotRunRegistry:
    """Retain at most one robot run until its explicit release."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._run: ActiveRobotRun | None = None

    def add(self, run: ActiveRobotRun) -> bool:
        with self._lock:
            if self._run is not None:
                return False
            self._run = run
            return True

    def get(self, run_id: UUID) -> ActiveRobotRun | None:
        with self._lock:
            run = self._run
            if run is None or run.coordinator.run_id != run_id:
                return None
            return run

    def release(self, run_id: UUID) -> ActiveRobotRun | None:
        with self._lock:
            run = self._run
            if run is None or run.coordinator.run_id != run_id:
                return None
            self._run = None
            return run

    def clear(self) -> None:
        with self._lock:
            self._run = None


def create_active_robot_run(
    detector: Detector,
    transform: Transform,
    run_id: UUID,
    context: ItemContext,
    started_at: float,
    nms_iou: float = 0.7,
) -> ActiveRobotRun:
    """Create isolated tracking and coordination around the shared detector."""

    if detector.manifest is None:
        raise ValueError("the loaded detector has no model manifest")

    support = InventoryDecisionSupport(
        labels=detector.manifest.labels,
        perception_version=detector.manifest.weights_sha256,
    )
    coordinator = RobotRunCoordinator(run_id, support, context)
    coordinator.start(started_at)
    return ActiveRobotRun(
        pipeline=Pipeline(
            detector=detector,
            transform=transform,
            task="detection-tracking",
            nms_iou=nms_iou,
        ),
        coordinator=coordinator,
    )
