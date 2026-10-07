# architecture constraints

> defines the cross-cutting rules that implementations must preserve to maintain product behavior, safety, and traceability.

| id | constraint |
|---|---|
| AC-001 | the robot and tray workflows shall share core perception, tracking, inventory, knowledge, and decision contracts while retaining separate lifecycle and timing logic. |
| AC-002 | perception, tracking and item resolution, inventory, instrument knowledge, policy evaluation, and operator presentation shall remain separate responsibilities. |
| AC-003 | all mutable tracking, inventory, and workflow state shall belong to exactly one run or session and shall not leak into another. |
| AC-004 | robot inventory and handling results shall be emitted incrementally; tray inventory and handling results shall be published only after explicit finalization. |
| AC-005 | each resolved physical item shall contribute to inventory exactly once, and each published inventory entry shall have one handling outcome. |
| AC-006 | model, label map, preprocessing, instrument knowledge, handling policy, schemas, and configuration shall be loaded as an explicitly versioned and compatible release set. |
| AC-007 | uncertainty, missing information, unsupported items, missing policy, or conflicting inputs shall remain explicit and shall not be converted into a recommendation. |
| AC-008 | SURGINT shall expose handling guidance to the robot operator but shall not issue robot motion, actuation, or execution commands. |
| AC-009 | frame intake, processing queues, and retained workflow state shall be bounded; overload shall produce declared degraded behavior rather than unbounded delay. |
| AC-010 | edge and cloud packaging may differ, but both deployment profiles shall preserve the same domain meaning, provenance, and failure semantics. |
| AC-011 | operational telemetry shall not contain raw media, credentials, or identifying information by default and shall not block the primary workflow. |
| AC-012 | distributed infrastructure, durable workflow storage, and automatic retraining shall not be introduced without an approved product or operational requirement. |
