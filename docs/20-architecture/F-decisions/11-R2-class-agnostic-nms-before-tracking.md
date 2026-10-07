# decision: allow class-agnostic NMS before tracking

**status:** accepted

**roadmap milestone:** R2: stateful inventory

## A. context

measured RT-DETR outputs contained overlapping duplicate boxes that opened multiple tracks for one instrument. Leaving them untouched preserved the detector's nominal NMS-free design but corrupted identity and inventory downstream.

## B. decision

support configurable class-agnostic non-maximum suppression after detection decoding and before tracking. Treat the NMS threshold as part of the evaluated runtime profile. Evaluation and serving must use the same configured behavior when making comparable claims.

## C. consequences

duplicate tracks and false inventory entries can decrease. NMS can also suppress genuinely overlapping instruments, so stronger suppression is not automatically better. The deployed system no longer claims a strictly NMS-free perception path.

## D. validation or reversal

compare detection recall, MOTA, IDF1, fragmentation, and inventory error with and without NMS. Disable or replace it if representative overlap cases show greater loss than the duplicate reduction provides.
