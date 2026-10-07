# product experience

> defines the operator-facing workflows, visible system states, outputs, terminology, and interaction qualities expected from the product.

## A. experience goal

operators should understand the current state, the latest resolved item, the inventory, and anything requiring review without seeing model or policy internals.

## B. continuous robot operation

- start and stop one continuous processing run.
- show the current item, its resolution state, and the resulting handling output with minimal delay.
- update the inventory once per resolved physical item.
- keep unresolved items visible as requiring review.
- allow the operator to inspect the current run and export its final summary.

## C. instrument-tray inventory

1. **capture:** choose a live camera or recorded video and scan the full tray.
2. **review context:** confirm procedure stage, item usage, and contamination context.
3. **finalize:** review inventory counts grouped by recommended handling or manual review.

during capture, update overlays and the visible-item list automatically. Keep confidence, explanations, matched rules, and technical JSON behind optional details.

## D. shared interaction principles

- keep the current state and next action obvious.
- use plain but domain-specific operational language.
- separate recommendations from items that need review.
- make failures actionable and preserve a safe stop or restart path.
- keep `PROTOTYPE` and `NOT FOR CLINICAL USE` visible.
- never translate low confidence, missing information, missing policy, or unsupported items into a recommendation.

## F. visual character

the interface should feel calm, legible, and operational rather than futuristic. user-friendliness and readability matter more than decoration or dense analytics.

