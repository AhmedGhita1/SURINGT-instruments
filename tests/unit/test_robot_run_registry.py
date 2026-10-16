from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.api.robot_runs import RobotRunRegistry, create_active_robot_run
from surgint.decision import ItemContext
from surgint.model.transform import Transform
from surgint.runtime.temporal import (
    FrameDimensionError,
    FrameIdentity,
    FrameOrderError,
    SourceIdentityError,
)


class FakeDetector:
    def __init__(self) -> None:
        self.manifest = SimpleNamespace(
            labels=("scalpel",),
            weights_sha256="sha256:" + "a" * 64,
        )


def active_run():
    return create_active_robot_run(
        detector=FakeDetector(),
        transform=Transform([640, 640]),
        run_id=uuid4(),
        context=ItemContext(workflow_stage="post-procedure-clearing"),
        started_at=10.0,
    )


def test_registry_retains_one_run_until_release():
    registry = RobotRunRegistry()
    first = active_run()
    second = active_run()

    assert registry.add(first)
    assert not registry.add(second)
    assert registry.get(first.coordinator.run_id) is first
    assert registry.get(second.coordinator.run_id) is None
    assert registry.release(first.coordinator.run_id) is first
    assert registry.add(second)
    assert second.pipeline is not first.pipeline
    assert second.pipeline.tracker is not first.pipeline.tracker


def test_robot_run_applies_shared_source_dimension_and_order_rules():
    run = active_run()
    first = FrameIdentity("robot-camera", 0, 1.0, 1920, 1080)

    assert run.resolve_frame_identity(first, 1920, 1080) is first
    run.record_frame_identity(first)

    with pytest.raises(FrameDimensionError, match="do not match"):
        run.resolve_frame_identity(
            FrameIdentity("robot-camera", 1, 1.2, 1280, 720),
            1920,
            1080,
        )
    with pytest.raises(SourceIdentityError, match="run source"):
        run.resolve_frame_identity(
            FrameIdentity("other-camera", 1, 1.2, 1920, 1080),
            1920,
            1080,
        )
    with pytest.raises(FrameOrderError, match="sequence"):
        run.resolve_frame_identity(
            FrameIdentity("robot-camera", 0, 1.2, 1920, 1080),
            1920,
            1080,
        )
    with pytest.raises(FrameOrderError, match="strictly advance"):
        run.resolve_frame_identity(
            FrameIdentity("robot-camera", 1, 0.9, 1920, 1080),
            1920,
            1080,
        )
