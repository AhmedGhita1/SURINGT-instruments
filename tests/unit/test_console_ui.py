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


def source_between(start: str, end: str) -> str:
    source = console_source()
    return source.split(start, 1)[1].split(end, 1)[0]


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


def test_camera_and_recorded_video_share_one_analysis_loop() -> None:
    source = console_source()

    assert 'startCapture(video, "camera")' in source
    assert 'startCapture(video, "video")' in source
    assert "await runAnalysis(video)" in source
    for removed in (
        "function runCamera",
        "function runVideo",
        "createLatestFrameScheduler",
        "/display-predictions",
        "liveGeneration",
        "INFERENCE_FRAME_STRIDE",
        "surgintLiveConfig",
    ):
        assert removed not in source


def test_loop_selects_frames_on_a_source_time_grid() -> None:
    loop = source_between("async function runAnalysis", "function finishCapture")

    assert "const ANALYSIS_INTERVAL_SECONDS = 0.2;" in console_source()
    assert "video.requestVideoFrameCallback(onFrame)" in loop
    assert "selectIfDue(live ? now / 1000 : metadata.mediaTime)" in loop
    assert loop.index("selectIfDue(video.currentTime)") < loop.index("await video.play()")
    assert "let gridStart = live ? null : 0" in loop
    assert "due >= gridIndex * ANALYSIS_INTERVAL_SECONDS" in loop
    assert "gridIndex = Math.floor(due / ANALYSIS_INTERVAL_SECONDS) + 1" in loop


def test_loop_keeps_one_request_in_flight() -> None:
    loop = source_between("async function runAnalysis", "function finishCapture")
    select = loop.split("const select = function (sourceTime) {", 1)[1].split(
        "const onFrame", 1
    )[0]

    assert "let inFlight = null" in loop
    assert "inFlight = framePromise.then(postFrame).then(acceptResult)" in loop
    assert "inFlight = null" in loop
    skip = "if (inFlight && live) {"
    assert skip in select
    assert select.index(skip) < select.index("captureFrame(video, sourceTime)")
    assert "analysisTiming.skipped_selections += 1" in select
    assert "video.pause()" in select
    assert "inFlight.then(function () {" in select
    assert "analysisTiming.paused_ms += performance.now() - pausedAt" in select
    assert select.index("analyze(frame);\n      void video.play()") > select.index("video.pause()")


def test_results_from_an_earlier_source_or_after_stop_are_ignored() -> None:
    accept = source_between("function acceptResult", "function setState")

    guard = "if (!running || result.frame.source_id !== sourceIdentity) {"
    assert guard in accept
    assert accept.index(guard) < accept.index("updateDetections(result.detections)")
    assert accept.index(guard) < accept.index("frames = result.frame_count")
    assert "sourceIdentity = null" in source_between("function resetSessionData", "function releaseMedia")
    assert "running = false" in source_between("function releaseMedia", "async function failCapture")


def test_stale_live_overlays_are_hidden_and_shown_as_delayed() -> None:
    source = console_source()

    assert "const MAX_OVERLAY_AGE_SECONDS = 0.4;" in source
    assert 'mediaKind === "camera" && latestCapturedAt !== null' in source
    assert "performance.now() / 1000 - latestCapturedAt" in source
    assert "overlayAgeSeconds() <= MAX_OVERLAY_AGE_SECONDS ? latestDetections : []" in source
    assert '"Results delayed"' in source
    assert "showResultsDelayed(age > MAX_OVERLAY_AGE_SECONDS)" in source
    assert "draw(video, visibleDetections())" in source
    assert ".live-status.delayed" in source


def test_console_records_a_small_timing_summary() -> None:
    source = console_source()

    assert "MAX_TIMING_SAMPLES = 1000" in source
    assert "window.surgintTiming = analysisTiming" in source
    assert 'response.headers.get("Server-Timing")' in source
    assert "capture_to_result_ms: performance.now() - completed.timing.capture_started_at" in source
    for counter in (
        "selections",
        "skipped_selections",
        "paused_ms",
        "stale_overlay_frames",
        "max_overlay_age_ms",
    ):
        assert f"{counter}: 0" in source


def test_console_sends_complete_client_temporal_metadata() -> None:
    source = console_source()

    for field in (
        'body.append("schema_version", "1.1")',
        'body.append("source_id", frame.source_id)',
        'body.append("sequence", String(frame.sequence))',
        'body.append("captured_at", String(frame.captured_at))',
        'body.append("source_width", String(frame.source_width))',
        'body.append("source_height", String(frame.source_height))',
    ):
        assert field in source

    assert "sequence: sourceSequence" in source
    assert "sourceSequence += 1" in source
    assert "sourceIdentity = kind + \":\" + session" in source


def test_recorded_video_reports_a_file_that_stops_decoding() -> None:
    loop = source_between("async function runAnalysis", "function finishCapture")
    handler = loop.split('video.addEventListener("error"', 1)[1]

    assert "showAlert(" in handler
    assert "formatElapsed(video.currentTime)" in handler


def test_native_video_plays_under_a_box_overlay_redrawn_per_result() -> None:
    source = console_source()
    loop = source_between("async function runAnalysis", "function finishCapture")
    accept = source_between("function acceptResult", "function setState")
    draw = source_between("function draw(video, detections, withFrame)", "function humanize")

    assert ".stage video, .stage canvas {" in source
    assert "object-fit: contain" in source
    assert "canvas.before(video)" in source
    assert "source.remove()" in source
    assert "context.clearRect(0, 0, canvas.width, canvas.height)" in draw
    assert "if (withFrame) {" in draw
    assert "draw(source, visibleDetections())" in accept
    on_frame = loop.split("const onFrame = function (now, metadata) {", 1)[1]
    assert "if (showResultsDelayed(age > MAX_OVERLAY_AGE_SECONDS)) {" in on_frame
    assert on_frame.count("draw(") == 1
    finish = source_between("function finishCapture", "async function discardCurrentSession")
    assert finish.index("draw(source, visibleDetections(), true)") < finish.index("releaseMedia()")
