from pathlib import Path


ROBOT_CONSOLE = Path("services/api/static/robot.html")


def source() -> str:
    return ROBOT_CONSOLE.read_text(encoding="utf-8")


def test_robot_console_is_a_separate_monitor_without_frame_or_execution_controls():
    page = source()

    assert "SURGINT · ROBOT WORKFLOW" in page
    assert "Handling guidance only" in page
    assert "Robot motion, actuation, execution, and safety controls remain outside" in page
    assert 'fetch(apiUrl("/v1/robot-runs")' in page
    assert "/frames" not in page
    assert "WebSocket" not in page


def test_robot_console_presents_live_results_inventory_reviews_and_failures():
    page = source()

    for text in (
        "Latest resolved item",
        "Append-only inventory",
        "Unresolved confirmed evidence",
        "Run condition",
        "timing_condition",
        "status.failure",
        'result.handling_outcome === "Needs review"',
        "No action issued.",
    ):
        assert text in page


def test_robot_console_handles_stop_summary_export_and_release():
    page = source()

    assert 'apiUrl(`/v1/robot-runs/${runId}/stop`)' in page
    assert 'apiUrl(`/v1/robot-runs/${runId}/export`)' in page
    assert 'method: "DELETE"' in page
    assert "Stopped run summary" in page
    assert "Download JSON" in page
    assert "summary.ended_at - summary.started_at" in page


def test_robot_console_keeps_research_safety_language_visible():
    page = source()

    assert "RESEARCH PROTOTYPE" in page
    assert "NOT FOR CLINICAL USE" in page
    assert "not clinical or safety-critical reconciliation" in page
