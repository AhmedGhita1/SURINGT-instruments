from dataclasses import dataclass, field
from threading import Lock

from surgint.model.detector import Detector
from surgint.model.transform import Transform
from surgint.runtime.decision_support import InventoryDecisionSupport
from surgint.runtime.pipeline import Pipeline
from surgint.runtime.session import DecisionSupportSession
from surgint.runtime.temporal import (
    FrameDimensionError,
    FrameIdentity,
    FrameOrderError,
    MetadataOrigin,
    SourceIdentityError,
)


@dataclass
class ActiveSession:
    """state owned by one sequence of frames."""

    pipeline: Pipeline
    decision_support: DecisionSupportSession
    lock: Lock = field(default_factory=Lock, repr=False)
    source_id: str | None = None
    last_sequence: int | None = None
    last_captured_at: float | None = None

    def resolve_frame_identity(
        self,
        identity: FrameIdentity | None,
        legacy_source_id: str,
        source_width: int,
        source_height: int,
    ) -> FrameIdentity:
        """Validate client metadata or synthesize an explicit compatibility identity."""
        if identity is None:
            if self.pipeline.tracker is None:
                raise RuntimeError("legacy temporal metadata requires a tracking pipeline")
            sequence = 0 if self.last_sequence is None else self.last_sequence + 1
            captured_at = (
                0.0
                if self.last_captured_at is None
                else self.last_captured_at + self.pipeline.tracker.nominal_interval_seconds
            )
            identity = FrameIdentity(
                source_id=legacy_source_id,
                sequence=sequence,
                captured_at=captured_at,
                source_width=source_width,
                source_height=source_height,
                origin=MetadataOrigin.SERVER_GENERATED_LEGACY,
            )

        if identity.source_size != (source_width, source_height):
            raise FrameDimensionError(
                "declared source dimensions "
                f"{identity.source_width}x{identity.source_height} do not match decoded frame "
                f"{source_width}x{source_height}"
            )
        if self.source_id is not None and identity.source_id != self.source_id:
            raise SourceIdentityError(
                f"session source is {self.source_id!r}, not {identity.source_id!r}"
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


def create_active_session(
    detector: Detector,
    transform: Transform,
    nms_iou: float = 0.7,
) -> ActiveSession:
    """create isolated tracking and decision state around a shared model."""
    if detector.manifest is None:
        raise ValueError("the loaded detector has no model manifest")

    support = InventoryDecisionSupport(
        labels=detector.manifest.labels,
        perception_version=detector.manifest.weights_sha256,
    )
    return ActiveSession(
        pipeline=Pipeline(
            detector=detector,
            transform=transform,
            task="detection-tracking",
            nms_iou=nms_iou,
        ),
        decision_support=DecisionSupportSession(support),
    )
