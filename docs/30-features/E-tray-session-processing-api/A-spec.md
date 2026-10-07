# feature package: tray-session processing api

> defines the service interface that owns tray-session state, frame processing, finalization, and resource limits.

**status:** implemented

**roadmap relationship:** R5: tray workflow MVP

## A. outcome

an operator client can create an isolated tray session, submit images or recorded video, receive tracked detections, finalize inventory decisions once, and release the session through a bounded API.

## B. sub-features

### B.1 API-01: service health and model readiness

**definition:** Distinguishes a running API process from one that has loaded a usable model artifact.

**specification:**

- Expose separate liveness and readiness endpoints.
- Refuse session creation until the configured checkpoint and its manifest load successfully.

**verification:** Health tests cover ready and not-ready startup states and packaged console delivery.

### B.2 API-02: isolated session lifecycle

**definition:** Creates and releases independent processing state around one shared detector.

**specification:**

- Assign each session a UUID and isolate its pipeline, tracker, inventory, decision lifecycle, and lock.
- Enforce a configured session limit and release capacity when a session is deleted.

**verification:** API tests cover creation, deletion, unknown sessions, limits, and capacity recovery.

### B.3 API-03: image-frame processing

**definition:** Processes one uploaded image through detection and tracking inside an open session.

**specification:**

- Decode input as RGB, run shared-model inference under the global inference lock, then update only the target session.
- Return frame count and aligned tracked detections without mutating state for an invalid image.

**verification:** Frame tests cover tracked output, invalid input, frame counts, and session mutation.

### B.4 API-04: recorded-video processing

**definition:** Decodes and samples one uploaded video and processes its frames in inference batches.

**specification:**

- Enforce byte and sampled-frame limits before replacing session state.
- Preserve frame order and commit the working session only after the complete video succeeds.

**verification:** Video tests cover batching, sampling, empty and invalid media, limits, and failure atomicity.

### B.5 API-05: one-shot session finalization

**definition:** Freezes the session inventory and resolves handling outcomes from submitted context.

**specification:**

- Return one class-level inventory result with count, confidence, outcome, action, reason, rule, and missing fields.
- Reject more input and a second finalization after the session has finalized.

**verification:** Finalization tests cover results, context, immutable lifecycle, and post-finalization rejection.

### B.6 API-06: bounded runtime behavior

**definition:** Limits retained sessions, uploaded media, sampled frames, inference concurrency, and mutable state.

**specification:**

- Use configured positive limits and reject oversized work explicitly.
- Keep one shared detector while serializing model inference and isolating session mutation.

**verification:** Settings and API tests cover invalid limits, concurrent state boundaries, and resource rejection paths.

## C. shared constraints

- Preserve ADRs `17` through `19` and requirements `FR-001`, `FR-002`, `FR-201` through `FR-205`, `OR-003`, and `OR-102`.
- The API remains a transport layer over runtime contracts and does not own perception or policy semantics.
- Finalization publishes complete results only; partial decision results remain internal.

## D. package acceptance

- readiness prevents work without a valid model.
- sessions remain isolated while sharing the detector safely.
- image and video inputs update tracking in source order and invalid inputs do not corrupt session state.
- finalization returns a complete immutable result and prevents later mutation.
- configured resource limits produce explicit client errors.

## E. non-goals

- robot workflow coordination;
- durable session storage or recovery after process restart;
- multi-worker or distributed coordination;
- authentication and public-network hardening;
- operator presentation, which belongs to the tray operator package.
