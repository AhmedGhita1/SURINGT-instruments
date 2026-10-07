# UC-001: continuous robot operation

**User:** Robot operator.

**Situation:** A robot processes surgical instruments continuously, usually one item at a time, while several items may occasionally be visible.

**Outcome:** Each resolved physical item produces one timely handling decision and one incremental inventory update.

## A. main flow

1. The robot operator starts a run and supplies a continuous video stream.
2. SURGINT detects, classifies, and tracks visible instruments.
3. SURGINT resolves a physical item using the available observation and context.
4. SURGINT presents the handling result and updated inventory to the robot operator.
5. The process continues without finalizing the session after each item.
6. When the run ends, the operator exports the final inventory and decision summary.

## B. exceptions

- An item is uncertain, unsupported, or lacks required information or policy: return a review outcome and do not invent a handling action.
- Several items are visible: preserve identity and avoid duplicate decisions or inventory entries.
- Processing cannot meet the required timing: expose degraded status rather than silently accumulating delay.
- The runtime or input fails: stop producing decisions and surface the failure to the robot operator.

## C. boundary

SURGINT provides perception and handling guidance. The robot operator remains responsible for robot operation, motion safety, and execution.
