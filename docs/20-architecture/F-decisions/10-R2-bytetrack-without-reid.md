# decision: use lightweight ByteTrack without appearance re-identification

**status:** accepted

**roadmap milestone:** R2: stateful inventory

## A. context

inventory requires physical identity across frames. Frame-level detections cannot distinguish a persistent item from repeated observations. Appearance re-identification or camera-motion compensation could strengthen identity but would add trained artifacts, latency, calibration, and data requirements.

## B. decision

use a two-pass ByteTrack design with constant-velocity Kalman prediction and IoU-based Hungarian association. High-score detections may create tracks; lower-score detections may rescue established tracks. Association remains class-agnostic, while track-level voting stabilizes the reported class. Do not emit prediction-only tracks, and reset all tracking state between sequences.

## C. consequences

the tracker is deterministic, inspectable, and inexpensive enough for the first runtime. It may fragment or swap identities under dense overlap, long disappearance, abrupt camera motion, or visually similar crossings. A missed observation remains distinct from predicted presence.

## D. validation or reversal

measure IDF1, identity switches, fragmentation, missed tracks, and runtime cost on representative sequences. Add ReID, uncertainty gating, or motion compensation only when measured failures justify their data and latency costs.
