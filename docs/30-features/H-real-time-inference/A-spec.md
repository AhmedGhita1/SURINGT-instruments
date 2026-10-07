# feature package: real-time inference

> defines the shared timing, scheduling, tracking, and output contracts for live and recorded video inference.

**status:** proposed

**roadmap relationship:** shared capability for R4 robot operation and R5 tray processing

## A. outcome

live video produces fresh perception and tracking outputs without accumulating delay, while recorded video remains deterministic and both modes preserve trustworthy inventory and decision evidence.

## B. sub-features

### B.1 RTI-01: temporal frame and result identity

**definition:** Identifies when every selected frame was captured and which result belongs to it.

**specification:**

- Each selected frame shall carry a source identity, monotonic sequence, monotonic capture timestamp, and source dimensions.
- Each result shall retain those values and expose the timestamps needed to measure queueing, processing, delivery, and display age.

**verification:** Contract tests demonstrate round-trip temporal identity, source isolation, monotonic ordering, and rejection of invalid or mismatched metadata.

### B.2 RTI-02: independent display and inference clocks

**definition:** Keeps source presentation responsive while admitting only a sustainable subset of frames to inference.

**specification:**

- Display shall advance independently of detector completion at the source-supported presentation rate.
- One frame may be processing and only the newest pending live frame may be retained; a newer frame shall overwrite an obsolete pending frame.
- Completed detector results shall enter tracking in capture order.

**verification:** Load tests show bounded pending work, counted overwrites, ordered results, and no growth in result age during sustained input.

### B.3 RTI-03: timestamp-aware tracking

**definition:** Advances track motion according to elapsed source time rather than one fixed step per detector update.

**specification:**

- Apply each detector measurement at its capture timestamp and calculate Kalman prediction using the actual elapsed time between measurements.
- Predict track state forward to a requested display timestamp without treating that prediction as a new observation.
- Confirmation and loss limits shall retain validated elapsed-time meaning when the selected detector rate changes.

**verification:** Controlled variable-rate sequences cover prediction, correction, confirmation delay, expiration, skipped detector frames, and deterministic replay.

### B.4 RTI-04: separate display and domain outputs

**definition:** Distinguishes predicted boxes used for current-frame display from confirmed observations used by product state.

**specification:**

- Display outputs shall identify their state timestamp, prediction age, track state, and uncertainty or validity condition.
- Inventory and decision support shall consume only confirmed detector-backed observations, never display-only predictions.
- Display prediction shall not mutate observation history, track evidence, inventory, or decisions.

**verification:** Integration tests prove that display-rate predictions move overlays without increasing observation counts or producing inventory and decision events.

### B.5 RTI-05: live freshness and degraded behavior

**definition:** Prevents old or uncertain spatial results from being presented as current.

**specification:**

- Compute displayed result age from capture time and suppress overlays beyond the approved age or uncertainty limit.
- Expose degraded state when the selected detector rate, result-age limit, or stream capacity cannot be maintained.
- Reduce admitted work before permitting an unbounded queue or silently increasing latency.

**verification:** Delayed and overloaded scenarios show stale-overlay suppression, explicit degraded state, bounded work, and recovery when timing returns within limits.

### B.6 RTI-06: deterministic recorded-video processing

**definition:** Processes retained video for repeatable results and exact frame-to-result alignment rather than live freshness.

**specification:**

- Process selected frames deterministically and in source order without the live overwrite policy.
- Render each result on its matching source frame; processing may run slower than nominal playback.
- Use the same detector, tracking, inventory, and temporal contracts as live mode.

**verification:** Repeated processing of the same video produces the same ordered results and draws every overlay on the frame identified by its sequence and timestamp.

### B.7 RTI-07: real-time evaluation profile

**definition:** Measures temporal behavior together with tracking and inventory quality under representative motion.

**specification:**

- Evaluate initial detector-selection rates of 5, 6, and 10 FPS before choosing the supported rate.
- Record effective detector rate, p50 and p95 capture-to-result latency, displayed overlay age, overwritten frames, prediction error, identity switches, confirmation delay, and inventory accuracy.
- Choose numerical freshness and quality limits from representative measurements before acceptance.

**verification:** A versioned evaluation report identifies the hardware, model, source profile, configuration, metrics, limits, and pass or fail result.

## C. shared constraints

- Preserve requirements `FR-002` through `FR-005`, `OR-102` through `OR-104`, `QR-001` through `QR-003`, `QR-102`, `QR-103`, `QR-201`, and `QR-202`.
- Preserve `AC-001`, `AC-003`, `AC-005`, `AC-009`, and `AC-010`.
- The shared runtime shall contain no robot-only or tray-only lifecycle behavior.
- Ordinary request-response serving remains the initial transport unless measurements prove it cannot satisfy the approved profile.

## D. package acceptance

- sustained live input retains at most one processing frame and one pending newest frame without increasing result age over time.
- frame and result identity remains correct across capture, inference, tracking, delivery, and display.
- tracking prediction uses elapsed time and remains deterministic for the same timestamped sequence.
- display predictions never create inventory entries or handling decisions.
- overlays beyond the approved age or uncertainty limit are suppressed and degraded operation remains visible.
- recorded video produces deterministic, source-aligned results without applying the live overwrite policy.
- the approved evaluation profile meets its numerical freshness, tracking, confirmation, and inventory limits.
- existing tray finalization and decision behavior remains unchanged apart from consuming the new temporal contracts.

## E. non-goals

- processing every live source frame;
- robot-run coordination or robot-operator behavior, which belong to the robot workflow package;
- a new detector, ontology, handling policy, or training workflow;
- appearance re-identification or camera-motion compensation;
- WebSockets, a dedicated inference server, distributed queues, or additional model workers without measured need;
- TensorRT, ONNX conversion, quantization, or robot-edge optimization;
- clinical or hard real-time guarantees.
