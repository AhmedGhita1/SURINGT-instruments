from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["alive", "ready", "not_ready"]


class SessionCreatedResponse(BaseModel):
    session_id: UUID


class TrackedDetectionResponse(BaseModel):
    track_id: int
    class_id: int
    label: str
    score: float
    box: tuple[float, float, float, float]


class FrameIdentityResponse(BaseModel):
    source_id: str
    sequence: int
    captured_at: float
    source_width: int
    source_height: int
    metadata_origin: Literal["client", "server-generated-legacy"]


class ResultTimingResponse(BaseModel):
    clock: Literal["server-monotonic"] = "server-monotonic"
    received_at: float
    processing_started_at: float
    processing_completed_at: float
    result_created_at: float


class FrameProcessedResponse(BaseModel):
    schema_version: Literal["1.1"] = "1.1"
    frame: FrameIdentityResponse
    timing: ResultTimingResponse
    frame_count: int
    detections: list[TrackedDetectionResponse]


class VideoProcessedResponse(BaseModel):
    frame_count: int


class ItemContextOverrideRequest(BaseModel):
    product_id: str | None = None
    lifecycle: Literal["reusable", "single-use"] | None = None


class FinalizeSessionRequest(BaseModel):
    workflow_stage: Literal[
        "pre-procedure-setup",
        "in-procedure",
        "post-procedure-clearing",
    ]
    use_state: Literal["unused", "used"] | None = None
    contamination_state: Literal[
        "not-regulated",
        "potentially-infectious",
        "chemical",
        "cytotoxic",
        "radioactive",
    ] | None = None
    overrides: dict[int, ItemContextOverrideRequest] = Field(default_factory=dict)


class FinalizedItemResponse(BaseModel):
    class_id: int
    label: str
    count: int
    confidence: float
    outcome: str
    action: str | None
    reason: str
    matched_rule: str | None
    missing_fields: list[str]


class FinalizedSessionResponse(BaseModel):
    frame_count: int
    items: list[FinalizedItemResponse]


class StartRobotRunRequest(BaseModel):
    workflow_stage: Literal[
        "pre-procedure-setup",
        "in-procedure",
        "post-procedure-clearing",
    ]
    use_state: Literal["unused", "used"] | None = None
    contamination_state: Literal[
        "not-regulated",
        "potentially-infectious",
        "chemical",
        "cytotoxic",
        "radioactive",
    ] | None = None
    product_id: str | None = None
    lifecycle: Literal["reusable", "single-use"] | None = None


class RobotItemResultResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: UUID
    item_id: int
    class_id: int
    label: str
    confidence: float
    resolution_sequence: int
    source_id: str
    source_sequence: int
    captured_at: float
    handling_outcome: Literal["Recommendation", "Needs review"]
    workflow_stage: str
    decision_intent: str
    decision_outcome: str
    concept_iri: str | None
    lifecycle: str | None
    sharp_hazard: str | None
    roles: list[str]
    action: str | None
    matched_rule: str | None
    missing_fields: list[str]
    reason: str
    perception_version: str
    ontology_version: str
    policy_id: str
    policy_version: str


class RobotInventoryEntryResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: UUID
    item_id: int
    class_id: int
    label: str
    resolution_sequence: int
    captured_at: float
    class_count: int
    handling_outcome: Literal["Recommendation", "Needs review"]
    action: str | None
    reason: str


class RobotRunStatusResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: UUID
    state: Literal["ready", "active", "degraded", "failed", "stopped"]
    timing_condition: Literal[
        "waiting-for-image",
        "current",
        "analysis-delayed",
        "image-stream-stopped",
        "terminal",
    ]
    frame_count: int
    result_count: int
    latest_received_source_at: float | None
    latest_analyzed_source_at: float | None
    failure: str | None


class RobotRunResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    status: RobotRunStatusResponse
    results: list[RobotItemResultResponse]
    inventory: list[RobotInventoryEntryResponse]


class RobotFrameProcessedResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    frame: FrameIdentityResponse
    timing: ResultTimingResponse
    detections: list[TrackedDetectionResponse]
    status: RobotRunStatusResponse
    new_results: list[RobotItemResultResponse]
    new_inventory_entries: list[RobotInventoryEntryResponse]


class RobotRunSummaryResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    research_warning: Literal[
        "Research prototype only. Not for clinical use or safety-critical instrument accounting."
    ] = "Research prototype only. Not for clinical use or safety-critical instrument accounting."
    run_id: UUID
    state: Literal["stopped"]
    started_at: float
    ended_at: float
    frame_count: int
    results: list[RobotItemResultResponse]
    inventory: list[RobotInventoryEntryResponse]
