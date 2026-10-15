from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from surgint.decision import ItemContext
from surgint.runtime.decision_support import InventoryDecisionSupport
from surgint.runtime.robot import (
    RobotRunCoordinator,
    RobotRunState,
    RobotTimingCondition,
)
from surgint.runtime.temporal import FrameIdentity
from tests.factories import tracked_frame


def coordinator(**context_overrides) -> RobotRunCoordinator:
    context_values = {"workflow_stage": "post-procedure-clearing"}
    context_values.update(context_overrides)
    run = RobotRunCoordinator(
        run_id=uuid4(),
        support=InventoryDecisionSupport(
            labels=["scalpel", "gauze"],
            perception_version="detector-v1+tracker-v1",
        ),
        context=ItemContext(**context_values),
    )
    run.start(10.0)
    return run


def frame(sequence: int, captured_at: float) -> FrameIdentity:
    return FrameIdentity(
        source_id="robot-camera",
        sequence=sequence,
        captured_at=captured_at,
        source_width=1920,
        source_height=1080,
    )


def resolve(run, identity, detections, received_at, completed_at):
    run.record_received(identity, received_at)
    return run.resolve_frame(identity, detections, completed_at)


def test_confirmed_track_emits_one_result_and_inventory_entry_exactly_once():
    run = coordinator(lifecycle="reusable", contamination_state="not-regulated")

    first = resolve(
        run,
        frame(0, 0.0),
        tracked_frame([0], [7], [0.91]),
        received_at=10.1,
        completed_at=10.2,
    )
    repeated = resolve(
        run,
        frame(1, 0.2),
        tracked_frame([0], [7], [0.96]),
        received_at=10.3,
        completed_at=10.4,
    )

    assert len(first) == 1
    assert repeated == ()
    assert [item.item_id for item in run.results] == [7]
    assert [entry.item_id for entry in run.inventory] == [7]
    assert run.inventory[0].class_count == 1


def test_simultaneous_confirmations_use_track_id_resolution_order():
    run = coordinator(use_state="unused", contamination_state="not-regulated")

    publications = resolve(
        run,
        frame(0, 0.0),
        tracked_frame([1, 0], [9, 3], [0.88, 0.91]),
        received_at=10.1,
        completed_at=10.2,
    )

    results = [result for result, _entry in publications]
    assert [result.item_id for result in results] == [3, 9]
    assert [result.resolution_sequence for result in results] == [1, 2]
    assert [entry.resolution_sequence for _result, entry in publications] == [1, 2]


def test_review_result_preserves_reason_without_an_action():
    run = coordinator()

    ((result, entry),) = resolve(
        run,
        frame(0, 0.0),
        tracked_frame([0], [7], [0.4]),
        received_at=10.1,
        completed_at=10.2,
    )

    assert result.decision.outcome == "low_confidence"
    assert result.handling_outcome == "Needs review"
    assert result.action is None
    assert result.reason == "score 0.40 is below 0.50"
    assert entry.handling_outcome == "Needs review"
    assert entry.action is None
    assert entry.reason == result.reason


def test_item_fields_and_terminal_summary_stay_frozen():
    run = coordinator(lifecycle="reusable", contamination_state="not-regulated")
    ((result, entry),) = resolve(
        run,
        frame(0, 1.25),
        tracked_frame([0], [7], [0.91]),
        received_at=10.1,
        completed_at=10.2,
    )

    resolve(
        run,
        frame(1, 1.45),
        tracked_frame([1], [7], [0.99]),
        received_at=10.3,
        completed_at=10.4,
    )
    summary = run.stop(10.5)

    assert result.class_id == 0
    assert result.confidence == pytest.approx(0.91)
    assert result.captured_at == pytest.approx(1.25)
    assert result.decision.perception_version == "detector-v1+tracker-v1"
    assert result.decision.ontology_version.endswith("/3.0.0")
    assert result.decision.policy_version == "2.1.0"
    assert summary.results == (result,)
    with pytest.raises(FrozenInstanceError):
        result.class_id = 1
    with pytest.raises(FrozenInstanceError):
        entry.class_count = 2
    with pytest.raises(FrozenInstanceError):
        summary.frame_count = 3


def test_status_applies_both_degraded_rules_and_recovers_on_fresh_result():
    run = coordinator(lifecycle="reusable", contamination_state="not-regulated")

    waiting = run.status(10.999)
    assert waiting.state is RobotRunState.ACTIVE
    assert waiting.timing_condition is RobotTimingCondition.WAITING_FOR_IMAGE
    stopped_stream = run.status(11.0)
    assert stopped_stream.state is RobotRunState.DEGRADED
    assert stopped_stream.timing_condition is RobotTimingCondition.IMAGE_STREAM_STOPPED

    first = frame(0, 1.0)
    resolve(
        run,
        first,
        tracked_frame([], [], []),
        received_at=11.1,
        completed_at=11.2,
    )
    assert run.status(11.2).state is RobotRunState.ACTIVE

    boundary = frame(1, 1.4)
    run.record_received(boundary, 11.3)
    assert run.status(11.3).state is RobotRunState.ACTIVE
    run.resolve_frame(boundary, tracked_frame([], [], []), 11.4)

    delayed = frame(2, 1.81)
    run.record_received(delayed, 11.5)
    delayed_status = run.status(11.5)
    assert delayed_status.state is RobotRunState.DEGRADED
    assert delayed_status.timing_condition is RobotTimingCondition.ANALYSIS_DELAYED

    run.resolve_frame(delayed, tracked_frame([], [], []), 11.6)
    recovered = run.status(11.6)
    assert recovered.state is RobotRunState.ACTIVE
    assert recovered.timing_condition is RobotTimingCondition.CURRENT
    with pytest.raises(FrozenInstanceError):
        recovered.frame_count = 4


def test_failure_is_terminal_and_prevents_new_results():
    run = coordinator()

    summary = run.fail("detector unavailable", 10.2)

    assert summary.state is RobotRunState.FAILED
    assert summary.failure == "detector unavailable"
    assert run.status(10.3).failure == "detector unavailable"
    with pytest.raises(RuntimeError, match="not active"):
        run.record_received(frame(0, 0.0), 10.3)
