# quality requirements

> defines how product correctness, timing, reliability, usability, reproducibility, and compatibility are measured.

numeric targets depend on the selected hardware and input profile. Each release acceptance profile must define them before that release can be accepted.

## A. measurement profile

| id | requirement |
|---|---|
| QR-001 | each workflow acceptance profile shall declare the hardware, input source, resolution, frame rate, concurrency, and supported operating conditions used for verification. |
| QR-002 | each acceptance profile shall define numerical targets for end-to-end latency, throughput, allowed backlog, resource use, startup, and recovery where they affect that workflow. |
| QR-003 | timing evidence shall report at least median and tail behavior and shall identify the exact timestamps and boundaries used in each measurement. |

## B. perception and inventory quality

| id | requirement |
|---|---|
| QR-101 | perception evaluation shall report class-level results and known failure conditions on a versioned evaluation set rather than only aggregate performance. |
| QR-102 | stateful evaluation shall measure identity preservation, item-resolution correctness, inventory count error, duplicate rate, and unresolved-item rate on representative sequences. |
| QR-103 | multi-item, overlapping, entering, leaving, and reappearing cases shall be included when those conditions are supported by the workflow. |

## C. runtime and decision quality

| id | requirement |
|---|---|
| QR-201 | robot timing shall be measured from the accepted input that completes item resolution until the result and inventory update are available to the robot operator. |
| QR-202 | tray timing shall measure source-to-overlay synchronization and shall verify that stale results are not presented as current. |
| QR-203 | identical resolved-item facts, context, policy, and versions shall produce the same handling outcome. |
| QR-204 | repeated finalization requests for the same completed tray session shall not create different or duplicated results. |
| QR-205 | incompatible artifact or schema versions shall be detected before results are produced. |

## D. operator experience and reproducibility

| id | requirement |
|---|---|
| QR-301 | workflow state, the next available action, failures, and `Needs review` outcomes shall remain distinguishable without opening technical details. |
| QR-302 | evaluation evidence shall identify the code, model, data, configuration, instrument knowledge, and policy versions needed to reproduce it. |
