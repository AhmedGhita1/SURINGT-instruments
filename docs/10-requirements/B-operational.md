# operational requirements

> defines the deployment, runtime, recovery, and operational visibility required to run the product safely and reproducibly.

## A. deployment

| id | requirement |
|---|---|
| OR-001 | the robot workflow shall support deployment on the selected robot edge hardware, while the tray workflow shall support deployment on a Hugging Face Space GPU or a local workstation GPU. |
| OR-002 | each deployment shall use a compatible, versioned set of application code, model artifacts, instrument knowledge, handling policy, schemas, and configuration. |
| OR-003 | the runtime shall validate required configuration, artifact compatibility, and input availability before accepting a run or session. |
| OR-004 | builds and deployments used for acceptance shall be reproducible from version-controlled definitions and declared artifact versions. |

## B. runtime and recovery

| id | requirement |
|---|---|
| OR-101 | the runtime shall expose startup, ready, active, degraded, failed, and stopped states where applicable. |
| OR-102 | frame intake, processing queues, and retained session state shall be bounded by the active deployment profile. |
| OR-103 | when processing cannot keep pace with the input, the runtime shall expose degraded operation and apply the declared overload behavior instead of silently accumulating delay. |
| OR-104 | a critical input or runtime failure shall stop new item resolutions and surface an actionable failure to the affected operator. |
| OR-105 | stopping or discarding a run shall release its resources, and restarting shall create isolated state rather than reuse the failed or completed run. |

## C. operational visibility

| id | requirement |
|---|---|
| OR-201 | operational records shall correlate each error, resolved item, decision, and timing measurement with its run or session and deployed artifact versions. |
| OR-202 | operational records shall exclude credentials, raw image or video content, and identifying information by default. |
| OR-203 | when persistent monitoring is enabled, telemetry delivery shall not block or determine the success of the primary workflow. |
| OR-204 | before exposure to untrusted clients, the deployment shall define and verify authentication, transport protection, request limits, and session-lifecycle controls. |
