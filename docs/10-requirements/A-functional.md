# functional requirements

> defines the required system behavior shared across the robot and tray workflows.

## A. shared behavior

| id | requirement |
|---|---|
| FR-001 | the system shall create an independent run or session for each started workflow and shall not carry inventory or decision state into a new one. |
| FR-002 | the system shall accept continuous live video for robot operation and supported live or recorded video for tray processing. |
| FR-003 | the system shall produce instrument observations containing the predicted class, confidence, source time, and tracking identity when tracking is active. |
| FR-004 | the system shall preserve physical item identity across frames and shall keep simultaneously visible items distinct. |
| FR-005 | the system shall add each resolved physical item to the inventory exactly once within a run or session. |
| FR-006 | the system shall resolve each inventory item against the available instrument knowledge, operator context, and handling policy. |
| FR-007 | the system shall return `Needs review` instead of a handling recommendation when evidence, context, instrument support, or policy is insufficient. |
| FR-008 | each resolved result shall retain the item identity, class, confidence, relevant context, artifact versions, policy result, and explanation needed to trace how it was produced. |

## B. continuous robot operation

| id | requirement |
|---|---|
| FR-101 | the robot operator shall be able to start and stop a continuous processing run. |
| FR-102 | the system shall present one result to the robot operator for each resolved physical item as soon as that item is resolved. |
| FR-103 | each result shall produce the corresponding incremental inventory update without finalizing the run. |
| FR-104 | the robot operator shall be able to see the run state, latest resolved item, latest handling outcome, current inventory, and unresolved items. |
| FR-105 | when the run ends, the system shall provide the robot operator with the final inventory and handling-decision summary for review and export. |

## C. instrument-tray inventory

| id | requirement |
|---|---|
| FR-201 | during capture, the system shall display the selected source with synchronized detections and tracks and shall update the visible-item list. |
| FR-202 | the tray operator shall be able to finish or discard a tray capture session. |
| FR-203 | before finalization, the system shall collect and validate the required procedure stage, item-usage, and contamination context. |
| FR-204 | finalization shall freeze one inventory and one handling outcome for each resolved inventory entry. |
| FR-205 | the finalized result shall separate handling recommendations from `Needs review` items and shall show an explicit empty result when no items were resolved. |
| FR-206 | the tray operator shall be able to export an operator-readable report and a technical JSON result. |
