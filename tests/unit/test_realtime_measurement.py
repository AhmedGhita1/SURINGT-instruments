import pytest

from pipelines.measure_realtime import (
    parse_server_timing,
    replay_overlay_age,
    selection_indices,
    simulate_sequential_scheduler,
)


def test_parse_server_timing_reads_named_durations():
    assert parse_server_timing("receive;dur=1.250, inference;dur=80.5") == {
        "receive": 1.25,
        "inference": 80.5,
    }


def test_selection_indices_support_non_divisible_detector_rates():
    assert selection_indices(20, source_fps=20.0, detector_fps=6.0, duration_seconds=1.0) == [
        0,
        4,
        7,
        10,
        14,
        17,
    ]


def test_sequential_scheduler_skips_busy_candidates_without_overwriting():
    result = simulate_sequential_scheduler(
        service_ms=[300.0],
        detector_fps=10.0,
        display_fps=20.0,
        duration_seconds=1.0,
    )

    assert result["candidate_frames"] == 10
    assert result["admitted_frames"] == 4
    assert result["busy_source_frames"] == 6
    assert result["overwritten_frames"] == 0
    assert result["bounded_pending_frames"] == 0
    assert result["effective_detector_fps"] == pytest.approx(4.0)
    assert result["overlay_age_ms"]["p95"] >= 300.0


def test_overlay_replay_uses_only_results_completed_by_each_display_frame():
    result = replay_overlay_age(
        admissions=[(0.0, 0.1), (0.2, 0.3)],
        display_fps=10.0,
        duration_seconds=0.5,
    )

    assert result["count"] == 4
    assert result["p50"] == pytest.approx(150.0)
    assert result["max"] == pytest.approx(200.0)
