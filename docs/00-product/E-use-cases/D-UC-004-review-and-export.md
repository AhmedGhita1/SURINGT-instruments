# UC-004: review and export results

**User:** Demonstration operator, evaluator, or technical reviewer.

**Situation:** A session has been finalized and its result needs to be understood or retained.

**Outcome:** The user can review an operator-friendly result and export the appropriate record.

## A. main flow

1. The user reviews item types, counts, handling groups, and review-required items.
2. The user may open technical details to inspect confidence and explanations.
3. The user downloads an operator report or technical JSON when needed.
4. The user starts a new independent scan.

## B. exceptions

- An action is unknown or unsupported: group the item under `Needs review`.
- No items were finalized: show an explicit empty result rather than a blank panel.
- Technical detail is unavailable: retain the operator result and state what is missing.
