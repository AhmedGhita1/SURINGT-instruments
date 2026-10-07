# feature package: tray operator workflow

> defines the browser experience for capturing a tray, confirming context, finalizing results, and exporting them.

**status:** implemented

**roadmap relationship:** R5: tray workflow MVP

## A. outcome

a tray operator can complete the capture, context review, finalization, result review, and export workflow from one browser interface.

## B. sub-features

### B.1 UI-01: guided workflow stages

**definition:** Organizes the operator experience into capture, review, and finalize stages with explicit progress and available actions.

**specification:**

- Keep the current stage, completed stages, next action, and failure state visually distinct.
- Prevent actions that do not apply to the current session state.

**verification:** Console tests cover explicit states, completed-stage treatment, controls, and session lifecycle wiring.

### B.2 UI-02: live-camera and recorded-video capture

**definition:** Lets the operator scan a tray using a browser camera or a locally selected video.

**specification:**

- Capture RGB frames from the active source and submit them to the open tray session.
- Stop media resources and release the session when capture is discarded or replaced.

**verification:** Interface structure and API wiring tests cover both source controls and session cleanup paths.

### B.3 UI-03: visual detection and tracking overlay

**definition:** Draws the selected source and the latest tracked instrument results on one canvas.

**specification:**

- Scale boxes and labels to the displayed frame and allow overlays to be switched on or off.
- Keep only one inference request active while recorded video continues to display.

**verification:** Console tests cover required canvas, overlay controls, operator metrics, and frame-processing URLs.

### B.4 UI-04: context confirmation

**definition:** Collects the supported procedure stage, use state, and contamination context before finalization.

**specification:**

- Use only controlled values accepted by the decision contracts.
- Require explicit operator confirmation before sending context for finalization.

**verification:** Console tests cover labels, supported choices, terminology, and confirmation behavior.

### B.5 UI-05: inventory and handling results

**definition:** Presents finalized counts and separates handling recommendations from items requiring review.

**specification:**

- Group results by operator-readable action while retaining review status and optional technical detail.
- Present an explicit empty result when no inventory items were finalized.

**verification:** Result-mapping tests cover action groups, review treatment, inventory totals, and empty-state structure.

### B.6 UI-06: operator and technical exports

**definition:** Creates a concise operator-readable report and a detailed technical JSON result from the finalized session.

**specification:**

- Keep technical identifiers out of the operator report while preserving item counts, handling groups, and review status.
- Include context, generation time, and the complete finalized result in the technical export.

**verification:** Console tests cover operator-report fields, excluded details, review status, and both download controls.

## C. shared constraints

- Preserve requirements `FR-201` through `FR-206`, `QR-202`, `QR-301`, and `SR-001` through `SR-202`.
- Keep `PROTOTYPE` and `NOT FOR CLINICAL USE` visible throughout the workflow and reports.
- Operator presentation may simplify internal outcomes but must preserve the reason for review.

## D. package acceptance

- the operator can start either input source, observe overlays, finish or discard capture, confirm context, and finalize.
- recommendations and review items remain distinguishable and an empty inventory is explicit.
- invalid input or API failure produces an actionable state without presenting incomplete results as final.
- CSV and JSON downloads contain their intended operator and technical information.

## E. non-goals

- robot-operation controls;
- correction or editing of detected inventory;
- clinical workflow approval;
- persistent user accounts or session history;
- guaranteed playback-rate or overlay-latency performance on every browser and device.
