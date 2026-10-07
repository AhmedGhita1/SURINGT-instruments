# implementation plan

> defines the ordered construction of tracking on top of the perception runtime.

**status:** implemented

## A. foundation

the package consumes immutable frame-space detections from the perception pipeline.

## B. approach

1. implement deterministic box conversion and Kalman motion estimation.
2. implement IoU distance and Hungarian association.
3. add high-confidence association, low-confidence rescue, and explicit track states.
4. suppress duplicate detections before association and emit confirmed observed tracks only.
5. integrate the tracker into the frame pipeline with sequence reset.
6. add MOT evaluation and annotated session rendering.

## C. affected boundaries

- `surgint/runtime/kalman.py`, `surgint/runtime/bytetrack.py`, and `surgint/runtime/pipeline.py`;
- `surgint/model/boxes.py` and the `Detections` contract;
- session evaluation and rendering entry points.

## D. escalation conditions

adding ReID, changing identity semantics, making association class-aware, or emitting predicted tracks requires an architecture decision and new evaluation evidence.
