# feature package: multi-object tracking

> defines how detections become stable instrument tracks and how tracking quality is evaluated.

**status:** implemented

**roadmap relationship:** R2: stateful inventory

## A. outcome

ordered video frames produce confirmed instrument tracks with stable identities suitable for session inventory.

## B. sub-features

### B.1 TRK-01: motion-state estimation

**definition:** Maintains a constant-velocity estimate of each track's box between observed frames.

**specification:**

- Represent and update track position through the Kalman filter without depending on model code.
- Reject invalid geometry and keep conversions between boxes and measurements deterministic.

**verification:** Kalman tests cover initiation, prediction, projection, update, and repeated tracking.

### B.2 TRK-02: two-pass ByteTrack association

**definition:** Associates current detections with existing tracks using IoU-based Hungarian matching.

**specification:**

- Match high-confidence detections first and use lower-confidence detections only to rescue confirmed tracks.
- Create tracks only from eligible high-confidence detections and expire unmatched tracks after the configured buffer.

**verification:** Controlled sequences cover association, rescue, confirmation, loss, expiration, and reset.

### B.3 TRK-03: duplicate suppression before tracking

**definition:** Removes overlapping detections that would otherwise create multiple tracks for one visible instrument.

**specification:**

- Apply configurable class-agnostic NMS in original-frame coordinates before tracker updates.
- Preserve score order and alignment across boxes, scores, and class identifiers.

**verification:** NMS and pipeline tests demonstrate suppression without corrupting detection arrays.

### B.4 TRK-04: confirmed-track output

**definition:** Exposes only observed, confirmed tracks through the runtime detection contract.

**specification:**

- Stabilize the reported class using track-level evidence while keeping association class-agnostic.
- Do not emit tentative, lost, removed, or prediction-only tracks as current observations.

**verification:** Tracker tests cover confirmation thresholds, class changes, weak detections, output filtering, and stable identifiers.

### B.5 TRK-05: sequence evaluation and rendering

**definition:** Measures tracking behavior across complete sessions and renders annotated evidence for inspection.

**specification:**

- Reset tracking state between sessions and evaluate frames in source order.
- Report identity and association metrics separately from class accuracy and support annotated video output.

**verification:** Session evaluation and rendering tests cover ordering, resets, MOT metrics, and output generation.

## C. shared constraints

- Preserve ADRs `10` and `11` and requirements `FR-004`, `QR-102`, and `QR-103`.
- Tracking state belongs to one sequence and must be reset before another sequence.
- Tracking does not decide inventory count or handling policy.

## D. package acceptance

- one persistent visible instrument receives one confirmed identity across successive frames.
- several simultaneous instruments remain distinct under representative motion and overlap.
- weak detections may rescue a confirmed track but cannot create or prematurely confirm a new track.
- sequence evaluation reports misses, false tracks, identity switches, IDF1, and class accuracy.

## E. non-goals

- appearance re-identification;
- camera-motion compensation;
- recovery from every long disappearance, dense crossing, or complete occlusion;
- physical inventory counting or handling decisions.
