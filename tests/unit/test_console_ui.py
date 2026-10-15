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
    assert "requestVideoFrameCallback(showFrame)" in source
    assert "presentedFrames - lastInferenceFrame" in source


def test_console_records_bounded_capture_to_display_timing_and_capacity() -> None:
    source = console_source()

    assert "MAX_TIMING_SAMPLES = 1000" in source
    assert "window.surgintTiming" in source
    assert 'response.headers.get("Server-Timing")' in source
    assert "display_age_ms: performance.now() - timing.capture_started_at" in source
    assert "schedulerTiming.busy_source_frames += 1" in source
    assert "schedulerTiming.overwritten += 1" in source
    assert "schedulerTiming.shutdown_drops += 1" in source
    assert "schedulerTiming.max_pending" in source
    assert "schedulerSnapshot" in source
    for counter in (
        "selection_opportunities",
        "selected",
        "capture_busy_drops",
        "capture_errors",
        "admitted",
        "busy_source_frames",
        "overwritten",
        "shutdown_drops",
        "dropped",
        "completed",
        "accepted_results",
        "suppressed_results",
        "request_errors",
        "aborted_requests",
        "in_flight",
        "pending",
        "max_pending",
        "prediction_requests",
        "prediction_completed",
        "prediction_accepted",
        "prediction_suppressed",
        "prediction_errors",
        "prediction_aborted",
        "invalid_predictions",
        "stale_overlay_frames",
        "rendered_overlay_frames",
    ):
        assert f"{counter}: 0" in source


def test_console_sends_complete_client_temporal_metadata() -> None:
    source = console_source()

    for field in (
        'body.append("schema_version", "1.1")',
        'body.append("source_id", sourceIdentity)',
        'body.append("sequence", String(sourceSequence))',
        'body.append("captured_at", String(capturedAt))',
        'body.append("source_width", String(video.videoWidth))',
        'body.append("source_height", String(video.videoHeight))',
    ):
        assert field in source

    assert "sourceSequence += 1" in source
    assert "sourceIdentity = kind + \":\" + session" in source


def test_live_scheduler_has_one_in_flight_and_one_replaceable_pending_frame() -> None:
    scheduler = source_between(
        "function createLatestFrameScheduler",
        "function predictionSuppressionReason",
    )

    assert "let inFlight = null" in scheduler
    assert "let pending = null" in scheduler
    assert "if (!inFlight)" in scheduler
    assert "launch(frame)" in scheduler
    assert "if (pending)" in scheduler
    assert "pending = frame" in scheduler
    assert "const next = pending" in scheduler
    assert "launch(next)" in scheduler
    assert "schedulerTiming.overwritten += 1" in scheduler
    assert "schedulerTiming.max_pending = Math.max" in scheduler
    assert "pending: Boolean(pending)" in scheduler


def test_live_camera_uses_an_independent_display_and_selection_clock() -> None:
    camera = source_between("function runCamera", "async function runVideo")

    assert "1000 / configuredLiveDetectorFps()" in camera
    assert "video.requestVideoFrameCallback" in camera
    assert "window.requestAnimationFrame" in camera
    assert "draw(video, displayPredictionsFor(latestDisplayTimestamp))" in camera
    assert "requestCurrentDisplayPredictions(latestDisplayTimestamp, generation)" in camera
    assert "const capturedAt = latestDisplayTimestamp" in camera
    assert "activeCapture = captureLiveFrame(" in camera
    assert "scheduler.offer(frame)" in camera
    assert "await postLiveFrame" not in camera


def test_live_results_are_correlated_before_updating_detector_backed_state() -> None:
    validation = source_between(
        "function detectorResultSuppressionReason",
        "function createLatestFrameScheduler",
    )

    for contract_check in (
        'result.schema_version !== "1.1"',
        "result.frame.source_id !== frame.source_id",
        'result.frame.metadata_origin !== "client"',
        "result.frame.sequence !== frame.sequence",
        "result.frame.captured_at !== frame.captured_at",
        "result.frame.source_width !== frame.source_width",
        "result.frame.source_height !== frame.source_height",
        "result.frame.sequence <= latestAcceptedFrame.sequence",
    ):
        assert contract_check in validation

    assert "updateDetections(result.detections)" in validation
    assert "schedulerTiming.accepted_results += 1" in validation
    assert "schedulerTiming.suppressed_results += 1" in validation


def test_display_predictions_are_bounded_validated_and_display_only() -> None:
    source = console_source()
    prediction = source_between(
        "function predictionSuppressionReason",
        "function stopDisplayPredictionRequest",
    )
    request = source_between(
        "function requestCurrentDisplayPredictions",
        "function setState",
    )

    assert '"/display-predictions"' in source
    assert "if (displayPredictionRequest" in request
    assert "displayPredictionRequest = request" in request
    assert "latestDisplayTimestamp" in request
    assert "performance.now() / 1000" in request
    assert "predictionSuppressionReason(prediction, receivedAt)" in request
    assert "updateDetections" not in request
    assert "seenClasses" not in request

    assert 'prediction.validity !== "valid"' in prediction
    assert "prediction.box.every(Number.isFinite)" in prediction
    assert "prediction.box[2] <= prediction.box[0]" in prediction
    assert "displayedAt - prediction.state_timestamp" in prediction
    assert "age > configuredOverlayAgeSeconds()" in prediction


def test_invalidated_prediction_failure_cannot_mutate_new_session_counters() -> None:
    request = source_between(
        "function requestCurrentDisplayPredictions",
        "function setState",
    )
    error_handler = request.split("}).catch(function (error) {", 1)[1].split(
        "}).finally(function () {", 1
    )[0]

    identity_guard = "displayPredictionRequest !== request"
    generation_guard = (
        "!liveGenerationMatches(expected.generation, expected.session_id, expected.source_id)"
    )
    counter_update = "schedulerTiming.prediction_errors += 1"
    assert identity_guard in error_handler
    assert generation_guard in error_handler
    assert error_handler.index(identity_guard) < error_handler.index(counter_update)
    assert error_handler.index(generation_guard) < error_handler.index(counter_update)


def test_generation_token_and_finish_drain_invalidate_late_live_work() -> None:
    source = console_source()
    finish = source_between("async function finishCapture", "async function discardCurrentSession")

    assert "generation === liveGeneration" in source
    assert "liveGeneration += 1" in source
    assert "requestController.abort()" in source
    assert "await stop(false)" in finish
    assert "releaseMedia();" in finish


def test_live_stop_drains_and_drops_an_active_capture_before_release() -> None:
    camera = source_between("function runCamera", "async function runVideo")
    stop = camera.split("stopLiveCapture = async function (abortInFlight) {", 1)[1].split(
        "const scheduleDisplay", 1
    )[0]

    assert "let activeCapture = null" in camera
    assert "const captureToDrain = activeCapture" in stop
    assert "const schedulerStop = scheduler.stop(abortInFlight)" in stop
    assert "await captureToDrain" in stop
    assert "await schedulerStop" in stop
    assert stop.index("acceptingFrames = false") < stop.index("const captureToDrain")
    assert stop.index("scheduler.stop(abortInFlight)") < stop.index("await captureToDrain")

    capture = camera.split("activeCapture = captureLiveFrame(", 1)[1]
    assert "!acceptingFrames" in capture
    assert "schedulerTiming.shutdown_drops += 1" in capture
    assert "schedulerTiming.dropped += 1" in capture
    assert "if (acceptingFrames)" in capture
    assert capture.index("if (acceptingFrames)") < capture.index("reportError(error)")
    assert "activeCapture = null" in capture


def test_recorded_video_keeps_its_existing_sequential_scheduler() -> None:
    video = source_between("async function runVideo", "async function finishCapture")

    assert "let inferenceInFlight = false" in video
    assert "presentedFrames - lastInferenceFrame" in video
    assert "draw(video, latestDetections)" in video
    assert "const completed = await postFrame(video)" in video
    assert "liveScheduler" not in video
    assert "pending" not in video


def test_recorded_video_reports_a_file_that_stops_decoding() -> None:
    video = source_between("async function runVideo", "async function finishCapture")
    handler = video.split('video.addEventListener("error"', 1)[1]

    assert "showAlert(" in handler
    assert "formatElapsed(video.currentTime)" in handler
