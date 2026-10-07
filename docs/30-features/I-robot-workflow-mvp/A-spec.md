# feature package: robot workflow mvp

> defines robot-run coordination, incremental item results, operator visibility, and safe runtime behavior on top of shared real-time inference.

**status:** proposed

**roadmap relationship:** R4: robot workflow MVP

## A. outcome

a robot operator can start a continuous run, receive one timely handling outcome and inventory update for each resolved item, inspect current state, then stop and export the final summary.

## B. sub-features

### B.1 ROB-01: isolated robot-run lifecycle

**definition:** Owns the state and context of one continuous robot-processing run independently from tray sessions.

**specification:**

- Validate runtime readiness and required artifacts before creating an active run with a unique identity.
- Allow one active robot run in the MVP runtime and create new tracking, inventory, and result-sequence state for every run.

**verification:** Lifecycle tests cover successful start, readiness failure, active-run conflict, stop, failure, release, and isolated restart.

### B.2 ROB-02: real-time runtime integration

**definition:** Connects the robot coordinator to the shared timestamped inference and confirmed-track stream.

**specification:**

- Consume the live scheduling, temporal identity, tracking, freshness, and degraded-state contracts defined by `H-real-time-inference`.
- Use only confirmed detector-backed tracks for item resolution; display-only predictions shall not trigger robot results.

**verification:** Integration tests show correct temporal ordering, degraded propagation, and absence of robot events from display-only predictions.

### B.3 ROB-03: per-item resolution

**definition:** Determines when a confirmed tracked instrument becomes one immutable robot-workflow item.

**specification:**

- For the MVP, resolve an item when its track is first reported as confirmed.
- Freeze item identity, class, confidence, resolution sequence, source time, and artifact provenance at resolution.

**verification:** Controlled sequences cover tentative tracks, first confirmation, later observations, class evidence, and multiple simultaneous confirmations.

### B.4 ROB-04: incremental decision and inventory publication

**definition:** Publishes one handling outcome and one append-only inventory entry as soon as an item resolves.

**specification:**

- Emit each resolved track exactly once and make its result and inventory entry visible together.
- Preserve the internal reason for every `Needs review` outcome and expose no action unless the outcome is a recommendation.

**verification:** End-to-end tests cover exactly-once emission, deterministic ordering, recommendations, review outcomes, and atomic visibility.

### B.5 ROB-05: run state and failure behavior

**definition:** Exposes the current workflow condition and prevents decisions from failed or invalid processing.

**specification:**

- Expose applicable `ready`, `active`, `degraded`, `failed`, and `stopped` states with timing condition and actionable failure detail.
- Propagate real-time degradation without inventing results; move a critical processing failure to terminal failed state and prevent new results.

**verification:** Failure tests distinguish overload degradation, recoverable invalid input, critical failure, recovery, and terminal-state behavior.

### B.6 ROB-06: robot-operator interface and summary

**definition:** Presents live run state and final results without exposing robot execution commands.

**specification:**

- Show the latest resolved item, handling outcome, append-only inventory, unresolved confirmed evidence, timing condition, and failures.
- On stop, provide an immutable inventory and decision summary for review and technical JSON export with research warnings visible.

**verification:** A browser walkthrough covers start, live processing, review outcomes, degraded state, stop, summary, export, failure, and safety language.

## C. shared constraints

- Depend on the accepted contracts and verified profile in `H-real-time-inference`.
- Preserve requirements `FR-001` through `FR-008`, `FR-101` through `FR-105`, `OR-101` through `OR-105`, `QR-201`, and `SR-001` through `SR-202`.
- Preserve ADR `16` and constraints `AC-004`, `AC-005`, `AC-008`, and `AC-009`.

## D. package acceptance

- one confirmed track produces exactly one result and inventory entry during an active run; repeated observations and display predictions produce no duplicate.
- simultaneous confirmations produce distinct results in deterministic resolution order.
- uncertainty and missing support produce `Needs review` without an action.
- real-time degradation, malformed input, and critical failure follow their declared state and mutation behavior.
- stopping freezes the final summary, later input is rejected, and a new run begins with isolated state.
- the declared R4 execution profile reports median and tail timing through the shared real-time measurements.
- existing tray-session behavior remains unchanged.

## E. non-goals

- real-time scheduling, timestamp-aware tracking, or display prediction, which belong to `H-real-time-inference`;
- robot motion, actuation, planning, or execution control;
- Jetson packaging, hardware-specific optimization, or an edge-performance claim, which belong to R6;
- a new detector, ontology, policy language, or training workflow;
- durable run storage, distributed processing, public-network hardening, or multi-worker coordination.
