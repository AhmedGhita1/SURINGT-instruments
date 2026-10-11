"""Static contract tests for the packaged operator console."""

from html.parser import HTMLParser
from pathlib import Path


CONSOLE = Path(__file__).parents[2] / "services" / "api" / "static" / "index.html"


class ConsoleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.labels_for: set[str] = set()
        self.required_selects: set[str] = set()
        self.views: set[str] = set()
        self.buttons_without_type: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        if tag == "select" and "required" in values and element_id:
            self.required_selects.add(element_id)
        if values.get("data-view"):
            self.views.add(values["data-view"])
        if tag == "button" and "type" not in values:
            self.buttons_without_type.append(element_id)


def console_source() -> str:
    return CONSOLE.read_text(encoding="utf-8")


def console_parser() -> ConsoleParser:
    parser = ConsoleParser()
    parser.feed(console_source())
    return parser


def test_console_has_four_explicit_operator_states() -> None:
    source = console_source()
    parser = console_parser()

    assert parser.views == {"initial", "live", "review", "final"}
    assert '<body data-state="initial">' in source
    assert "Start a new scan" in source
    assert "Live scan" in source
    assert "Review handling context" in source
    assert "Inventory ready" in source
    assert 'const order = ["capture", "review", "finalize"]' in source


def test_completed_steps_fill_their_connecting_tracks() -> None:
    source = console_source()

    assert ".step.complete:not(:last-child)::after" in source
    assert "height: 5px;" in source
    assert "background: var(--success);" in source


def test_console_uses_approved_branding_and_operator_metrics() -> None:
    source = console_source()
    normalized = source.lower()

    assert "Surgical Intelligence" in source
    assert "PROTOTYPE" in source
    assert "NOT FOR CLINICAL USE" in source
    assert "objects in view" in normalized
    assert "elapsed" in normalized
    assert "frames processed" not in normalized
    assert "Research demonstration only. Not for clinical decisions." not in source


def test_context_inputs_are_labeled_and_require_confirmation() -> None:
    source = console_source()
    parser = console_parser()

    assert {"workflow-stage", "use-state", "contamination"} <= parser.labels_for
    assert parser.required_selects == {"workflow-stage", "use-state", "contamination"}
    assert "elements.contextForm.reset();" in source
    assert 'elements.generate.disabled = !valid' in source


def test_procedure_stages_use_clear_operator_facing_names() -> None:
    source = console_source()

    assert "Post-procedure — clearing the tray" in source
    assert "Intra-procedure — active instrument use" in source
    assert "Pre-procedure — setting up the tray" in source


def test_contamination_selector_only_exposes_supported_operator_choices() -> None:
    source = console_source()

    assert '<option value="not-regulated">No regulated contamination</option>' in source
    assert '<option value="potentially-infectious">Potentially infectious</option>' in source
    assert '<option value="chemical">' not in source
    assert '<option value="cytotoxic">' not in source
    assert '<option value="radioactive">' not in source


def test_interactive_controls_have_explicit_button_types_and_unique_ids() -> None:
    parser = console_parser()

    assert parser.buttons_without_type == []
    assert len(parser.ids) == len(set(parser.ids))


def test_console_has_responsive_and_accessible_status_treatment() -> None:
    source = console_source()

    assert "@media (max-width: 900px)" in source
    assert "@media (max-width: 600px)" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert 'role="alert"' in source
    assert 'role="status"' in source
    assert 'aria-current="step"' in source
    assert 'aria-pressed="true"' in source


def test_results_are_mapped_to_human_readable_action_groups() -> None:
    source = console_source()

    for label in (
        "Needs review",
        "Secure for reprocessing",
        "Send for reprocessing",
        "Sharps disposal",
        "General waste",
    ):
        assert label in source

    assert "renderTechnicalDetails(finalized.items)" in source
    assert "Download report" in source
    assert "Download technical JSON" in source


def test_operator_report_excludes_technical_fields_and_preserves_review_status() -> None:
    source = console_source()
    report_builder = source.split("function buildOperatorReport()", 1)[1].split(
        "function csvCell", 1
    )[0]

    assert 'handling: "Manual review required"' in source
    assert 'status: "Needs review"' in source
    assert '["Item", "Count", "Recommended handling", "Status"]' in source
    assert '"surgical-intelligence-inventory-report.csv"' in source
    assert '"surgical-intelligence-inventory-technical.json"' in source
    assert "Print / save PDF" not in source
    assert "function printOperatorReport()" not in source
    for technical_field in (
        "frame_count",
        "class_id",
        "confidence",
        "outcome",
        "matched_rule",
        "missing_fields",
    ):
        assert technical_field not in report_builder


def test_console_wires_session_lifecycle_through_signed_api_urls() -> None:
    source = console_source()

    assert 'get("__sign")' in source
    assert 'apiUrl("/v1/sessions")' in source
    assert '"/frames"' in source
    assert '"/finalize"' in source
    assert 'method: "DELETE"' in source
    assert "keepalive: true" in source
    assert "requestVideoFrameCallback(showFrame)" in source
    assert "presentedFrames - lastInferenceFrame" in source


def test_console_records_bounded_capture_to_display_timing_without_queueing() -> None:
    source = console_source()

    assert "MAX_TIMING_SAMPLES = 1000" in source
    assert "window.surgintTiming" in source
    assert 'response.headers.get("Server-Timing")' in source
    assert "display_age_ms: performance.now() - timing.capture_started_at" in source
    assert "schedulerTiming.busy_source_frames += 1" in source
    assert "schedulerTiming.overwritten = 0" in source
