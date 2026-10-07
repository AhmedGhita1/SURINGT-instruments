# implementation plan

> defines the ordered construction of session inventory from confirmed tracks.

**status:** implemented

## A. foundation

the package consumes ordered tracked detections with stable track identifiers.

## B. approach

1. create a mutable per-session inventory keyed by track identity.
2. retain time, class, confidence, and simultaneous-visibility evidence on every update.
3. define the conservative class-level finalization rule and immutable result types.
4. enforce reset and detachment between mutable and finalized state.
5. add class-aware session inventory evaluation.

## C. affected boundaries

- `surgint/runtime/inventory.py`;
- `surgint/evaluation/inventory.py`;
- session evaluation and decision-support consumers.

## D. escalation conditions

changing the count heuristic, adding tracklet merging, allowing operator edits, or persisting inventory requires an approved product or architecture decision.
