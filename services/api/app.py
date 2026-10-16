import logging
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from services.api.schemas import (
    FinalizedItemResponse,
    FinalizedSessionResponse,
    FinalizeSessionRequest,
    FrameIdentityResponse,
    FrameProcessedResponse,
    HealthResponse,
    RobotFrameProcessedResponse,
    RobotInventoryEntryResponse,
    RobotItemResultResponse,
    RobotRunResponse,
    RobotRunStatusResponse,
    RobotRunSummaryResponse,
    ResultTimingResponse,
    SessionCreatedResponse,
    StartRobotRunRequest,
    TrackedDetectionResponse,
    VideoProcessedResponse,
)
from services.api.robot_runs import (
    ActiveRobotRun,
    RobotRunRegistry,
    create_active_robot_run,
)
from services.api.sessions import ActiveSession, create_active_session
from services.api.settings import ServingSettings
from services.api.video import InvalidVideoError, decode_sampled_frames
from surgint.decision import ItemContext, ItemContextOverride, SessionContext
from surgint.model.detector import Detector
from surgint.model.transform import Transform
from surgint.runtime.robot import (
    RobotInventoryEntry,
    RobotItemResult,
    RobotRunState,
    RobotRunStatus,
    RobotRunSummary,
)
from surgint.runtime.temporal import (
    FrameDimensionError,
    FrameIdentity,
    FrameOrderError,
    ResultTiming,
    SourceIdentityError,
    TemporalContractError,
)

logger = logging.getLogger(__name__)

CONSOLE = Path(__file__).parent / "static" / "index.html"
ROBOT_CONSOLE = Path(__file__).parent / "static" / "robot.html"


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000.0


def _server_timing_header(measurements: dict[str, float]) -> str:
    return ", ".join(f"{name};dur={duration:.3f}" for name, duration in measurements.items())


def _client_frame_identity(
    schema_version: str | None,
    source_id: str | None,
    sequence: int | None,
    captured_at: float | None,
    source_width: int | None,
    source_height: int | None,
) -> FrameIdentity | None:
    values = (schema_version, source_id, sequence, captured_at, source_width, source_height)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="temporal frame metadata must be supplied together",
        )
    if schema_version != "1.1":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="unsupported frame schema_version",
        )
    try:
        return FrameIdentity(
            source_id=source_id,
            sequence=sequence,
            captured_at=captured_at,
            source_width=source_width,
            source_height=source_height,
        )
    except TemporalContractError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


def _robot_item_response(item: RobotItemResult) -> RobotItemResultResponse:
    decision = item.decision
    return RobotItemResultResponse(
        run_id=item.run_id,
        item_id=item.item_id,
        class_id=item.class_id,
        label=item.label,
        confidence=item.confidence,
        resolution_sequence=item.resolution_sequence,
        source_id=item.source_id,
        source_sequence=item.source_sequence,
        captured_at=item.captured_at,
        handling_outcome=item.handling_outcome,
        workflow_stage=decision.workflow_stage,
        decision_intent=decision.decision_intent,
        decision_outcome=decision.outcome,
        concept_iri=decision.concept_iri,
        lifecycle=decision.lifecycle,
        sharp_hazard=decision.sharp_hazard,
        roles=list(decision.roles),
        action=decision.action,
        matched_rule=decision.matched_rule,
        missing_fields=list(decision.missing_fields),
        reason=decision.reason,
        perception_version=decision.perception_version,
        ontology_version=decision.ontology_version,
        policy_id=decision.policy_id,
        policy_version=decision.policy_version,
    )


def _robot_inventory_response(
    entry: RobotInventoryEntry,
) -> RobotInventoryEntryResponse:
    return RobotInventoryEntryResponse(
        run_id=entry.run_id,
        item_id=entry.item_id,
        class_id=entry.class_id,
        label=entry.label,
        resolution_sequence=entry.resolution_sequence,
        captured_at=entry.captured_at,
        class_count=entry.class_count,
        handling_outcome=entry.handling_outcome,
        action=entry.action,
        reason=entry.reason,
    )


def _robot_status_response(status_snapshot: RobotRunStatus) -> RobotRunStatusResponse:
    return RobotRunStatusResponse(
        run_id=status_snapshot.run_id,
        state=status_snapshot.state.value,
        timing_condition=status_snapshot.timing_condition.value,
        frame_count=status_snapshot.frame_count,
        result_count=status_snapshot.result_count,
        latest_received_source_at=status_snapshot.latest_received_source_at,
        latest_analyzed_source_at=status_snapshot.latest_analyzed_source_at,
        failure=status_snapshot.failure,
    )


def _robot_run_response(run: ActiveRobotRun, now: float) -> RobotRunResponse:
    return RobotRunResponse(
        status=_robot_status_response(run.coordinator.status(now)),
        results=[_robot_item_response(item) for item in run.coordinator.results],
        inventory=[
            _robot_inventory_response(entry) for entry in run.coordinator.inventory
        ],
    )


def _robot_summary_response(summary: RobotRunSummary) -> RobotRunSummaryResponse:
    return RobotRunSummaryResponse(
        run_id=summary.run_id,
        state="stopped",
        started_at=summary.started_at,
        ended_at=summary.ended_at,
        frame_count=summary.frame_count,
        results=[_robot_item_response(item) for item in summary.results],
        inventory=[_robot_inventory_response(entry) for entry in summary.inventory],
    )


def create_app(
    settings: ServingSettings | None = None,
    detector_loader: Callable[[Path], Detector] | None = None,
    video_decoder: Callable[[bytes, float], Iterable[np.ndarray]] | None = None,
) -> FastAPI:
    """create the local API and load the model during application startup."""
    settings = settings or ServingSettings.from_environment()
    detector_loader = detector_loader or Detector.from_checkpoint
    video_decoder = video_decoder or decode_sampled_frames

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.detector = None
        app.state.transform = None
        app.state.sessions: dict[UUID, ActiveSession] = {}
        app.state.sessions_lock = Lock()
        app.state.robot_runs = RobotRunRegistry()
        app.state.inference_lock = Lock()

        if settings.checkpoint is None:
            logger.warning("checkpoint loading is disabled; the API is not ready")
        else:
            try:
                detector = detector_loader(settings.checkpoint)
                detector.to(settings.device)
                detector.eval()
                if detector.manifest is None:
                    raise ValueError("the loaded detector has no model manifest")
                transform = Transform(
                    list(detector.manifest.input_size),
                    detector.manifest.pad_color,
                    detector.manifest.rescale_factor,
                )
                app.state.detector = detector
                app.state.transform = transform
                logger.info("loaded model from %s on %s", settings.checkpoint, settings.device)
            except Exception:
                logger.exception("failed to load model from %s", settings.checkpoint)

        yield
        with app.state.sessions_lock:
            app.state.sessions.clear()
        app.state.robot_runs.clear()
        app.state.detector = None
        app.state.transform = None

    application = FastAPI(title="Surgint API", version="1", lifespan=lifespan)

    @application.middleware("http")
    async def expose_server_timing(request: Request, call_next):
        """Expose per-frame phase durations without retaining image content."""
        started_at = perf_counter()
        request.state.server_timing_started_at = started_at
        response = await call_next(request)
        measurements = getattr(request.state, "server_timing", None)
        if measurements is not None:
            measurements["server"] = _elapsed_ms(started_at)
            response.headers["Server-Timing"] = _server_timing_header(measurements)
        return response

    @application.get("/", include_in_schema=False)
    def console() -> FileResponse:
        """Serve the page an operator runs a session from."""
        return FileResponse(CONSOLE)

    @application.get("/robot", include_in_schema=False)
    def robot_console() -> FileResponse:
        """Serve the robot-run monitoring page."""
        return FileResponse(ROBOT_CONSOLE)

    @application.get("/health/live", response_model=HealthResponse)
    def live() -> HealthResponse:
        return HealthResponse(status="alive")

    @application.get("/health/ready", response_model=HealthResponse)
    def ready(response: Response) -> HealthResponse:
        if application.state.detector is None:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(status="not_ready")
        return HealthResponse(status="ready")

    def robot_run_or_404(run_id: UUID) -> ActiveRobotRun:
        run = application.state.robot_runs.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="robot run not found",
            )
        return run

    @application.post(
        "/v1/robot-runs",
        response_model=RobotRunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def start_robot_run(request: StartRobotRunRequest) -> RobotRunResponse:
        detector = application.state.detector
        transform = application.state.transform
        if detector is None or transform is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="model is not ready",
            )

        try:
            context = ItemContext(
                workflow_stage=request.workflow_stage,
                use_state=request.use_state,
                contamination_state=request.contamination_state,
                product_id=request.product_id,
                lifecycle=request.lifecycle,
            )
        except (TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

        try:
            run = create_active_robot_run(
                detector=detector,
                transform=transform,
                run_id=uuid4(),
                context=context,
                started_at=perf_counter(),
                nms_iou=settings.nms_iou,
            )
        except Exception as error:
            logger.exception("robot run startup validation failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="robot run artifacts are not ready",
            ) from error

        if not application.state.robot_runs.add(run):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="release the current robot run before starting another",
            )
        return _robot_run_response(run, perf_counter())

    @application.get(
        "/v1/robot-runs/active",
        response_model=RobotRunResponse,
    )
    def get_active_robot_run() -> RobotRunResponse:
        run = application.state.robot_runs.current()
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="no active robot run",
            )
        with run.lock:
            current_status = run.coordinator.status(perf_counter())
            if current_status.state in {RobotRunState.FAILED, RobotRunState.STOPPED}:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="no active robot run",
                )
            return _robot_run_response(run, perf_counter())

    @application.get(
        "/v1/robot-runs/{run_id}",
        response_model=RobotRunResponse,
    )
    def get_robot_run(run_id: UUID) -> RobotRunResponse:
        run = robot_run_or_404(run_id)
        with run.lock:
            return _robot_run_response(run, perf_counter())

    @application.post(
        "/v1/robot-runs/{run_id}/frames",
        response_model=RobotFrameProcessedResponse,
    )
    def process_robot_frame(
        run_id: UUID,
        request: Request,
        image: Annotated[UploadFile, File()],
        schema_version: Annotated[Literal["1.1"] | None, Form()] = None,
        source_id: Annotated[str | None, Form()] = None,
        sequence: Annotated[int | None, Form()] = None,
        captured_at: Annotated[float | None, Form()] = None,
        source_width: Annotated[int | None, Form()] = None,
        source_height: Annotated[int | None, Form()] = None,
    ) -> RobotFrameProcessedResponse:
        request.state.server_timing = {
            "receive": _elapsed_ms(request.state.server_timing_started_at),
        }
        run = robot_run_or_404(run_id)
        client_identity = _client_frame_identity(
            schema_version,
            source_id,
            sequence,
            captured_at,
            source_width,
            source_height,
        )
        if client_identity is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="robot frames require temporal frame metadata",
            )

        try:
            phase_started_at = perf_counter()
            with Image.open(image.file) as uploaded:
                frame = np.asarray(uploaded.convert("RGB"))
            request.state.server_timing["decode"] = _elapsed_ms(phase_started_at)
        except (OSError, UnidentifiedImageError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid image",
            ) from error

        lock_started_at = perf_counter()
        if not run.lock.acquire(blocking=False):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="robot run is already processing a frame",
            )
        try:
            current_status = run.coordinator.status(perf_counter())
            if current_status.state in (RobotRunState.STOPPED, RobotRunState.FAILED):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"robot run is {current_status.state.value}",
                )
            try:
                frame_identity = run.resolve_frame_identity(
                    client_identity,
                    source_width=int(frame.shape[1]),
                    source_height=int(frame.shape[0]),
                )
            except FrameDimensionError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=str(error),
                ) from error
            except (SourceIdentityError, FrameOrderError) as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

            run.coordinator.record_received(frame_identity, perf_counter())
            try:
                with application.state.inference_lock:
                    request.state.server_timing["queue"] = _elapsed_ms(lock_started_at)
                    processing_started_at = perf_counter()
                    detections = run.pipeline.predict(
                        frame,
                        score_threshold=0.0,
                        captured_at=frame_identity.captured_at,
                    )
                pipeline_timing = run.pipeline.last_timing
                if pipeline_timing is not None:
                    request.state.server_timing.update(
                        {
                            "preprocess": pipeline_timing.preprocess_ms,
                            "inference": pipeline_timing.inference_ms,
                            "postprocess": pipeline_timing.postprocess_ms,
                            "tracking": pipeline_timing.tracking_ms,
                        }
                    )
                phase_started_at = perf_counter()
                publications = run.coordinator.resolve_frame(
                    frame_identity,
                    detections,
                    perf_counter(),
                )
                request.state.server_timing["inventory"] = _elapsed_ms(phase_started_at)
                run.record_frame_identity(frame_identity)
                processing_completed_at = perf_counter()
            except Exception as error:
                try:
                    run.coordinator.summary
                except RuntimeError:
                    run.coordinator.fail(
                        "frame processing failed; release this run and start a new one",
                        perf_counter(),
                    )
                logger.exception("robot frame processing failed for run %s", run_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="robot run failed during frame processing",
                ) from error

            labels = run.pipeline.detector.manifest.labels
            if detections.track_ids is None:
                raise RuntimeError("tracking pipeline returned detections without track ids")
            response_detections = [
                TrackedDetectionResponse(
                    track_id=int(track_id),
                    class_id=int(class_id),
                    label=labels[int(class_id)],
                    score=float(score),
                    box=tuple(float(coordinate) for coordinate in box),
                )
                for box, score, class_id, track_id in zip(
                    detections.boxes,
                    detections.scores,
                    detections.class_ids,
                    detections.track_ids,
                )
            ]
            result_created_at = perf_counter()
            timing = ResultTiming(
                received_at=request.state.server_timing_started_at,
                processing_started_at=processing_started_at,
                processing_completed_at=processing_completed_at,
                result_created_at=result_created_at,
            )
            return RobotFrameProcessedResponse(
                frame=FrameIdentityResponse(
                    source_id=frame_identity.source_id,
                    sequence=frame_identity.sequence,
                    captured_at=frame_identity.captured_at,
                    source_width=frame_identity.source_width,
                    source_height=frame_identity.source_height,
                    metadata_origin=frame_identity.origin.value,
                ),
                timing=ResultTimingResponse(
                    received_at=timing.received_at,
                    processing_started_at=timing.processing_started_at,
                    processing_completed_at=timing.processing_completed_at,
                    result_created_at=timing.result_created_at,
                ),
                detections=response_detections,
                status=_robot_status_response(run.coordinator.status(perf_counter())),
                new_results=[
                    _robot_item_response(result) for result, _entry in publications
                ],
                new_inventory_entries=[
                    _robot_inventory_response(entry) for _result, entry in publications
                ],
            )
        finally:
            run.lock.release()

    @application.post(
        "/v1/robot-runs/{run_id}/stop",
        response_model=RobotRunSummaryResponse,
    )
    def stop_robot_run(run_id: UUID) -> RobotRunSummaryResponse:
        run = robot_run_or_404(run_id)
        with run.lock:
            current_status = run.coordinator.status(perf_counter())
            if current_status.state is RobotRunState.FAILED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="failed robot run cannot be stopped",
                )
            if current_status.state is RobotRunState.STOPPED:
                return _robot_summary_response(run.coordinator.summary)
            return _robot_summary_response(run.coordinator.stop(perf_counter()))

    def stopped_robot_summary(run_id: UUID) -> RobotRunSummary:
        run = robot_run_or_404(run_id)
        with run.lock:
            current_status = run.coordinator.status(perf_counter())
            if current_status.state is not RobotRunState.STOPPED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="robot run must be stopped before requesting its summary",
                )
            return run.coordinator.summary

    @application.get(
        "/v1/robot-runs/{run_id}/summary",
        response_model=RobotRunSummaryResponse,
    )
    def get_robot_run_summary(run_id: UUID) -> RobotRunSummaryResponse:
        return _robot_summary_response(stopped_robot_summary(run_id))

    @application.get(
        "/v1/robot-runs/{run_id}/export",
        response_model=RobotRunSummaryResponse,
    )
    def export_robot_run(run_id: UUID, response: Response) -> RobotRunSummaryResponse:
        summary = stopped_robot_summary(run_id)
        response.headers["Content-Disposition"] = (
            f'attachment; filename="surgint-robot-run-{run_id}.json"'
        )
        return _robot_summary_response(summary)

    @application.delete(
        "/v1/robot-runs/{run_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def release_robot_run(run_id: UUID) -> Response:
        run = robot_run_or_404(run_id)
        with run.lock:
            try:
                run.coordinator.summary
            except RuntimeError as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="stop or fail the robot run before release",
                ) from error
            released = application.state.robot_runs.release(run_id)
        if released is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="robot run not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post(
        "/v1/sessions",
        response_model=SessionCreatedResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session() -> SessionCreatedResponse:
        detector = application.state.detector
        transform = application.state.transform
        if detector is None or transform is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="model is not ready",
            )

        with application.state.sessions_lock:
            if len(application.state.sessions) >= settings.max_sessions:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="active session limit reached",
                )
            session_id = uuid4()
            session = create_active_session(detector, transform, settings.nms_iou)
            application.state.sessions[session_id] = session
        return SessionCreatedResponse(session_id=session_id)

    @application.delete(
        "/v1/sessions/{session_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_session(session_id: UUID) -> Response:
        with application.state.sessions_lock:
            session = application.state.sessions.pop(session_id, None)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="session not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post(
        "/v1/sessions/{session_id}/frames",
        response_model=FrameProcessedResponse,
    )
    def process_frame(
        session_id: UUID,
        request: Request,
        image: Annotated[UploadFile, File()],
        schema_version: Annotated[Literal["1.1"] | None, Form()] = None,
        source_id: Annotated[str | None, Form()] = None,
        sequence: Annotated[int | None, Form()] = None,
        captured_at: Annotated[float | None, Form()] = None,
        source_width: Annotated[int | None, Form()] = None,
        source_height: Annotated[int | None, Form()] = None,
    ) -> FrameProcessedResponse:
        request.state.server_timing = {
            "receive": _elapsed_ms(request.state.server_timing_started_at),
        }
        with application.state.sessions_lock:
            session = application.state.sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="session not found",
            )

        try:
            phase_started_at = perf_counter()
            with Image.open(image.file) as uploaded:
                frame = np.asarray(uploaded.convert("RGB"))
            request.state.server_timing["decode"] = _elapsed_ms(phase_started_at)
        except (OSError, UnidentifiedImageError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid image",
            ) from error

        client_identity = _client_frame_identity(
            schema_version,
            source_id,
            sequence,
            captured_at,
            source_width,
            source_height,
        )

        lock_started_at = perf_counter()
        # one frame per session: a concurrent frame is rejected rather than queued
        if not session.lock.acquire(blocking=False):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="session is already processing a frame",
            )
        try:
            if session.decision_support.is_finalized:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="session has already been finalized",
                )
            try:
                frame_identity = session.resolve_frame_identity(
                    client_identity,
                    legacy_source_id=f"legacy:{session_id}",
                    source_width=int(frame.shape[1]),
                    source_height=int(frame.shape[0]),
                )
            except FrameDimensionError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=str(error),
                ) from error
            except (SourceIdentityError, FrameOrderError) as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error
            with application.state.inference_lock:
                request.state.server_timing["queue"] = _elapsed_ms(lock_started_at)
                processing_started_at = perf_counter()
                detections = session.pipeline.predict(
                    frame,
                    score_threshold=0.0,
                    captured_at=frame_identity.captured_at,
                )
            pipeline_timing = session.pipeline.last_timing
            if pipeline_timing is not None:
                request.state.server_timing.update(
                    {
                        "preprocess": pipeline_timing.preprocess_ms,
                        "inference": pipeline_timing.inference_ms,
                        "postprocess": pipeline_timing.postprocess_ms,
                        "tracking": pipeline_timing.tracking_ms,
                    }
                )
            phase_started_at = perf_counter()
            session.decision_support.update(detections)
            request.state.server_timing["inventory"] = _elapsed_ms(phase_started_at)
            frame_count = session.decision_support.frame_count
            session.record_frame_identity(frame_identity)
            processing_completed_at = perf_counter()
        finally:
            session.lock.release()

        labels = session.pipeline.detector.manifest.labels
        if detections.track_ids is None:
            raise RuntimeError("tracking pipeline returned detections without track ids")
        response_detections = [
            TrackedDetectionResponse(
                track_id=int(track_id),
                class_id=int(class_id),
                label=labels[int(class_id)],
                score=float(score),
                box=tuple(float(coordinate) for coordinate in box),
            )
            for box, score, class_id, track_id in zip(
                detections.boxes,
                detections.scores,
                detections.class_ids,
                detections.track_ids,
            )
        ]
        result_created_at = perf_counter()
        timing = ResultTiming(
            received_at=request.state.server_timing_started_at,
            processing_started_at=processing_started_at,
            processing_completed_at=processing_completed_at,
            result_created_at=result_created_at,
        )
        return FrameProcessedResponse(
            frame=FrameIdentityResponse(
                source_id=frame_identity.source_id,
                sequence=frame_identity.sequence,
                captured_at=frame_identity.captured_at,
                source_width=frame_identity.source_width,
                source_height=frame_identity.source_height,
                metadata_origin=frame_identity.origin.value,
            ),
            timing=ResultTimingResponse(
                received_at=timing.received_at,
                processing_started_at=timing.processing_started_at,
                processing_completed_at=timing.processing_completed_at,
                result_created_at=timing.result_created_at,
            ),
            frame_count=frame_count,
            detections=response_detections,
        )

    @application.post(
        "/v1/sessions/{session_id}/video",
        response_model=VideoProcessedResponse,
    )
    def process_video(
        session_id: UUID,
        video: Annotated[UploadFile, File()],
    ) -> VideoProcessedResponse:
        with application.state.sessions_lock:
            session = application.state.sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="session not found",
            )

        contents = video.file.read(settings.max_video_bytes + 1)
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="video is empty",
            )
        if len(contents) > settings.max_video_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="video exceeds the upload limit",
            )

        with session.lock:
            if session.decision_support.is_finalized:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="session has already been finalized",
                )
            if session.decision_support.frame_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="session already contains frames",
                )

            working = create_active_session(
                session.pipeline.detector,
                session.pipeline.transform,
                settings.nms_iou,
            )
            batch: list[np.ndarray] = []

            def process_batch() -> None:
                with application.state.inference_lock:
                    detections = working.pipeline.predict_batch(batch, score_threshold=0.0)
                for frame_detections in detections:
                    working.decision_support.update(frame_detections)
                batch.clear()

            try:
                sampled_frames = 0
                for frame in video_decoder(contents, settings.video_sample_fps):
                    sampled_frames += 1
                    if sampled_frames > settings.max_video_frames:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail="video exceeds the sampled-frame limit",
                        )
                    batch.append(frame)
                    if len(batch) == settings.video_batch_size:
                        process_batch()
                if batch:
                    process_batch()
            except InvalidVideoError as error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(error),
                ) from error

            if not working.decision_support.frame_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="video contains no decodable frames",
                )

            session.pipeline = working.pipeline
            session.decision_support = working.decision_support
            return VideoProcessedResponse(frame_count=session.decision_support.frame_count)

    @application.post(
        "/v1/sessions/{session_id}/finalize",
        response_model=FinalizedSessionResponse,
    )
    def finalize_session(
        session_id: UUID,
        request: FinalizeSessionRequest,
    ) -> FinalizedSessionResponse:
        with application.state.sessions_lock:
            session = application.state.sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="session not found",
            )

        context = SessionContext(
            workflow_stage=request.workflow_stage,
            use_state=request.use_state,
            contamination_state=request.contamination_state,
        )
        overrides = {
            class_id: ItemContextOverride(**override.model_dump())
            for class_id, override in request.overrides.items()
        }

        with session.lock:
            if session.decision_support.is_finalized:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="session has already been finalized",
                )
            try:
                result = session.decision_support.finalize(context, overrides)
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=str(error),
                ) from error

        labels = session.pipeline.detector.manifest.labels
        items = [
            FinalizedItemResponse(
                class_id=item.class_id,
                label=labels[item.class_id],
                count=item.inventory_item.count,
                confidence=item.inventory_item.score,
                outcome=item.decision.outcome,
                action=item.decision.action,
                reason=item.decision.reason,
                matched_rule=item.decision.matched_rule,
                missing_fields=list(item.decision.missing_fields),
            )
            for item in result.items
        ]
        return FinalizedSessionResponse(frame_count=result.frames, items=items)

    return application


app = create_app()
