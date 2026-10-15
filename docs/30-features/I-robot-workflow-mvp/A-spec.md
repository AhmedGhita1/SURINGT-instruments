# feature package: robot workflow mvp

> defines robot-run coordination, ROS image input, incremental item results, operator visibility, and safe runtime behavior on top of shared real-time inference.

**status:** proposed

**roadmap relationship:** R4: robot workflow MVP

## A. outcome

a robot operator can start a continuous run fed by images from the robot's ROS node, receive one timely handling outcome and inventory update for each resolved item, inspect current state, then stop and export the final summary.

## B. sub-features

### B.1 ROB-01: isolated robot-run lifecycle

**definition:** Owns the state and context of one continuous robot-processing run independently from tray sessions.

**specification:**

- Validate runtime readiness and required artifacts before creating an active run with a unique identity.
- Allow one active robot run in the MVP runtime and create new tracking, inventory, and result-sequence state for every run.

**verification:** Lifecycle tests cover successful start, readiness failure, active-run conflict, stop, failure, release, and isolated restart.

### B.2 ROB-02: ROS image input

**definition:** Brings camera images from the robot's ROS node into the shared real-time runtime.

**specification:**

- A small ROS bridge node subscribes to the robot's image topic and sends selected images to the robot-run frame endpoint. The SURGINT service itself contains no ROS code.
- The bridge applies the selection rule from `H-real-time-inference` RTI-02: one image per 0.2 seconds of source time, at most one request in flight, and a skipped image when a request is in flight or the server answers HTTP 429.
- Each sent image carries the temporal identity from RTI-01. The image header timestamp is its capture time.
- Item resolution uses only confirmed detector-backed tracks.
- **TBD:** the ROS version, the image topic, and its message type.

**verification:** Bridge tests with replayed image messages show selection by header time, one request in flight, counted skips, and results in capture order.

### B.3 ROB-03: per-item resolution

**definition:** Determines when a confirmed tracked instrument becomes one immutable robot-workflow item.

**specification:**

- For the MVP, resolve an item when its track is first reported as confirmed.
- Freeze item identity, class, confidence, resolution sequence, source time, and artifact provenance at resolution.

**verification:** Controlled sequences cover tentative tracks, first confirmation, later observations, class evidence, and multiple simultaneous confirmations.

### B.4 ROB-04: incremental decision and inventory publication

**definition:** Publishes one handling outcome and one append-only inventory entry as soon as an item resolves.

**specification:**

- Emit each resolved track exactly once and make its result and inventory entry visible together on the robot-operator page.
- Preserve the internal reason for every `Needs review` outcome and expose no action unless the outcome is a recommendation.
- **TBD:** whether results are also published back into ROS, and on which topic and message type.

**verification:** End-to-end tests cover exactly-once emission, deterministic ordering, recommendations, review outcomes, and atomic visibility.

### B.5 ROB-05: run state and failure behavior

**definition:** Exposes the current workflow condition and prevents decisions from failed or invalid processing.

**specification:**

- Expose applicable `ready`, `active`, `degraded`, `failed`, and `stopped` states with timing condition and actionable failure detail.
- The run is `degraded` while its latest analyzed image is more than 0.4 seconds behind the newest received image, or while no image has arrived for 1 second. It returns to `active` when fresh results arrive.
- Degradation never invents results. A critical processing failure moves the run to terminal `failed` and prevents new results.

**verification:** Failure tests distinguish overload degradation, a stopped image stream, recoverable invalid input, critical failure, recovery, and terminal-state behavior.

### B.6 ROB-06: robot-operator interface and summary

**definition:** Presents live run state and final results without exposing robot execution commands.

**specification:**

- Show the latest resolved item, handling outcome, append-only inventory, unresolved confirmed evidence, timing condition, and failures.
- On stop, provide an immutable inventory and decision summary for review and technical JSON export with research warnings visible.

**verification:** A browser walkthrough covers start, live processing, review outcomes, degraded state, stop, summary, export, failure, and safety language.

### B.7 ROB-07: R4 evaluation profile

**definition:** Declares the profile and targets used to accept the robot workflow.

**specification:**

- Profile: the local workstation GPU, one active run, and a recorded video replayed as ROS images at its native frame rate.
- Targets: at least 5 analyses per second, p95 time of at most 300 ms from the image that resolves an item until its result and inventory entry are visible on the operator page, and no queued images.
- Robot edge hardware is out of scope until it is selected.

**verification:** A versioned report identifies the hardware, model, input, configuration, metrics, and pass or fail result.

## C. shared constraints

- Depend on the accepted contracts and verified profile in `H-real-time-inference`.
- Preserve requirements `FR-001` through `FR-008`, `FR-101` through `FR-105`, `OR-101` through `OR-105`, `QR-201`, and `SR-001` through `SR-202`.
- Preserve ADR `16` and constraints `AC-004`, `AC-005`, `AC-008`, and `AC-009`.

## D. package acceptance

- one confirmed track produces exactly one result and inventory entry during an active run; repeated observations produce no duplicate.
- simultaneous confirmations produce distinct results in deterministic resolution order.
- uncertainty and missing support produce `Needs review` without an action.
- images from the ROS node reach the run through the bridge, following the shared selection rule.
- real-time degradation, a stopped image stream, malformed input, and critical failure follow their declared state and mutation behavior.
- stopping freezes the final summary, later input is rejected, and a new run begins with isolated state.
- the ROB-07 profile meets its targets.
- existing tray-session behavior remains unchanged.

## E. non-goals

- timestamp-aware tracking and the frame contracts, which belong to `H-real-time-inference`;
- ROS code inside the SURGINT service;
- robot motion, actuation, planning, or execution control;
- Jetson packaging, hardware-specific optimization, or an edge-performance claim, which belong to R6;
- a new detector, ontology, policy language, or training workflow;
- durable run storage, distributed processing, public-network hardening, or multi-worker coordination.
