# safety requirements

> defines the product boundaries, prohibited behavior, warning states, and safe failure rules required for a research prototype.

## A. product boundary

| id | requirement |
|---|---|
| SR-001 | the product shall identify itself as a research prototype and as not for clinical use in every operator-facing workflow and exported report. |
| SR-002 | the product shall not claim or provide clinical decisions, sterility assessment, autonomous safety decisions, or safety-critical instrument reconciliation. |
| SR-003 | outputs presented to the robot operator shall represent handling guidance or `Needs review`, not robot motion, actuation, or execution commands. |
| SR-004 | the robot operator shall remain responsible for authorizing robot actions; SURGINT shall not control motion, actuation, or execution. |

## B. uncertainty and failure behavior

| id | requirement |
|---|---|
| SR-101 | low confidence, unsupported instruments, missing context, missing policy, conflicting inputs, and insufficient evidence shall result in `Needs review`. |
| SR-102 | the system shall not translate an unknown, incomplete, degraded, or failed state into a handling recommendation. |
| SR-103 | invalid configuration or incompatible required artifacts shall prevent the affected workflow from starting. |
| SR-104 | after a critical runtime or input failure, the system shall stop producing new decisions until a new valid run or session is established. |
| SR-105 | partial, stale, or failed finalization results shall not be presented or exported as complete. |

## C. accountability

| id | requirement |
|---|---|
| SR-201 | every handling outcome shall be traceable to the resolved observation, supplied context, instrument knowledge, policy version, and matched rule or review reason. |
| SR-202 | the operator shall retain authority to review unresolved outcomes and to stop or discard a run or session. |
| SR-203 | product validation shall state supported conditions, unsupported conditions, known failure modes, and measured limitations alongside capability claims. |
