# feature package: real-time inference

> defines one analysis loop and the timing, tracking, and output contracts for live and recorded video inference.

**status:** proposed

**roadmap relationship:** shared capability for R4 robot operation and R5 tray processing

## A. outcome

live and recorded video both show live overlays from one simple analysis loop. Live video never accumulates delay, recorded video analyzes the same frames on every run, and both preserve trustworthy inventory and decision evidence.

## B. sub-features

### B.1 RTI-01: temporal frame and result identity

**definition:** Identifies when every selected frame was captured and which result belongs to it.

**specification:**

- Each selected frame shall carry a source identity, monotonic sequence, monotonic capture timestamp, and source dimensions.
- Each result shall retain those values and expose the timestamps needed to measure queueing, processing, delivery, and display age.

**verification:** Contract tests demonstrate round-trip temporal identity, source isolation, monotonic ordering, and rejection of invalid or mismatched metadata.

### B.2 RTI-02: one analysis loop

**definition:** Selects frames by source time and keeps at most one analysis request in flight, for live and recorded video alike. The rule is workflow-neutral: the tray page implements it here, and the robot coordinator implements it in the robot workflow package.

**specification:**

- Select one frame per analysis interval of source time. The initial interval is 0.2 seconds.
- Keep at most one analysis request in flight and never queue frames.
- When a selection is due while a request is in flight, live video skips it and recorded video pauses playback until the result returns.
- Completed results shall enter tracking in capture order.
- The frame endpoint rejects a frame with HTTP 429 when its session already has a frame processing. Clients treat the rejection as a skipped selection.
- Clients ignore a result whose source does not match the current source or that arrives after the run stopped.

**verification:** Browser runs show no overlapping requests, counted skipped selections for live video, and analyzed timestamps on the source-time grid for recorded video. An API test shows a concurrent frame for the same session is rejected, and a browser run shows a late result after discard does not change the new scan.

### B.3 RTI-03: timestamp-aware tracking

**definition:** Advances track motion according to elapsed source time rather than one fixed step per detector update.

**specification:**

- Apply each detector measurement at its capture timestamp and calculate Kalman prediction using the actual elapsed time between measurements.
- Confirmation and loss limits shall retain validated elapsed-time meaning when the analysis interval changes.

**verification:** Controlled variable-rate sequences cover prediction, correction, confirmation delay, expiration, skipped selections, and deterministic replay.

### B.4 RTI-04: live overlays from the latest result

**definition:** Draws the latest detector-backed tracked boxes over the playing video.

**specification:**

- The video plays natively, and a transparent overlay redraws boxes only when a new result arrives.
- Overlays show only detector-backed tracked boxes. There are no display-only predicted boxes.
- Inventory and decision support consume the same detector-backed observations as before.

**verification:** Browser runs at 4K and 720p show boxes aligned with their objects and no per-frame video redraw.

### B.5 RTI-05: live freshness

**definition:** Prevents old spatial results from being presented as current.

**specification:**

- Hide live overlays when the latest result is older than 0.4 seconds, measured from capture time, and show that results are delayed.
- Restore overlays when a fresh result arrives.

**verification:** A delayed-server scenario hides overlays, shows the delayed state, and recovers.

### B.6 RTI-06: repeatable recorded video

**definition:** Makes recorded-video results depend only on the file, not on playback timing.

**specification:**

- Selections fall on the same source-time grid on every run, using the first presented frame at or after each grid time.
- Overlays stay live and may trail the displayed frame by up to one analysis round trip.
- A file that stops decoding is reported with the time it stopped.

**verification:** Two runs of the same file, at 1080p and at 4K, analyze identical frame timestamps and produce the same final inventory.

### B.7 RTI-07: real-time evaluation profile

**definition:** Measures the loop together with tracking and inventory quality on each deployment profile.

**specification:**

- Acceptance profile: the local workstation GPU and one session, with a 720p fake camera, the 1080p synthetic demo, and the first 30 seconds of a 4K Magdeburg recording.
- Targets at 720p and 1080p: at least 5 analyses per second, p95 capture-to-result latency of at most 200 ms, live overlay age of at most 0.4 seconds, and no queued frames. 4K results are reported without a target.
- The Hugging Face Space profile is measured and reported without a target. The robot edge profile is measured in the robot workflow package once its hardware is selected.
- Record effective analysis rate, p50 and p95 capture-to-result latency, overlay age, skipped selections, paused playback time, identity switches, confirmation delay, and inventory accuracy.

**verification:** A versioned report identifies the hardware, model, sources, configuration, metrics, limits, and pass or fail result.

## C. shared constraints

- Preserve requirements `FR-002` through `FR-005`, `OR-102` through `OR-104`, `QR-001` through `QR-003`, `QR-102`, `QR-103`, `QR-201`, and `QR-202`.
- Preserve `AC-001`, `AC-003`, `AC-005`, `AC-009`, and `AC-010`.
- The shared runtime shall contain no robot-only or tray-only lifecycle behavior.
- Ordinary request-response serving remains the transport unless measurements prove it cannot satisfy the approved profile.

## D. package acceptance

- live and recorded video both show live overlays from the same analysis loop.
- at most one analysis request is in flight, and live result age does not grow over time.
- frame and result identity remains correct across capture, inference, tracking, delivery, and display.
- tracking uses elapsed time and remains deterministic for the same timestamped sequence.
- two runs of the same recorded file analyze identical frames and produce the same final inventory.
- the frame endpoint never processes or queues more than one frame per session.
- live overlays older than 0.4 seconds are hidden and the delayed state is visible.
- the evaluation report meets the RTI-07 targets on the local workstation GPU.
- existing tray finalization and decision behavior remains unchanged.

## E. non-goals

- processing every source frame;
- display-only predicted boxes between detector results;
- server-side processing of recorded files;
- robot-run coordination or robot-operator behavior, which belong to the robot workflow package;
- a new detector, ontology, handling policy, or training workflow;
- appearance re-identification or camera-motion compensation;
- WebSockets, a dedicated inference server, distributed queues, or additional model workers without measured need;
- TensorRT, ONNX conversion, quantization, or robot-edge optimization;
- clinical or hard real-time guarantees.
