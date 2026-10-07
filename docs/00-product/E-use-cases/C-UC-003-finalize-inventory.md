# UC-003: finalize the inventory

**User:** Demonstration operator or evaluator.

**Situation:** Capture is complete and the system needs context before producing handling guidance.

**Outcome:** The user receives one frozen inventory with a decision outcome for each item type.

## A. main flow

1. The system summarizes the completed scan.
2. The user confirms procedure stage, item usage, and contamination context.
3. The system validates the context and finalizes the session once.
4. The system groups item counts by recommended handling or `Needs review`.

## B. exceptions

- Required context is missing: do not finalize; identify the missing field.
- Evidence, information, or policy is insufficient: return an explicit review outcome rather than guessing.
- Finalization fails: preserve a clear error state and do not present partial results as complete.
