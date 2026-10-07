# implementation plan

> defines the smallest implementation path for robot coordination after the shared real-time runtime is available.

**status:** proposed

## A. foundation

the package depends on `H-real-time-inference` plus the existing model, tracking, inventory, ontology, policy, and decision contracts. The tray lifecycle remains separate and unchanged.

## B. approach

1. add immutable robot item-result, inventory-entry, run-summary, and status contracts.
2. add a robot-run coordinator around the shared confirmed-track stream.
3. resolve each newly confirmed item through existing decision support and publish its frozen result with its inventory entry.
4. add a bounded robot-run registry that reuses the shared detector and real-time runtime.
5. expose separate robot-run endpoints for start, state, stop, summary, export, and release.
6. add a robot-operator page that presents the approved run state and outputs.
7. add focused domain, API, failure, interface, real-time integration, and tray-regression tests.

## C. affected boundaries

- `surgint/runtime`: robot-run coordination and immutable robot result contracts;
- `services/api`: robot-run registry, schemas, endpoints, and operator page;
- `tests`: lifecycle, exactly-once behavior, decision, failure, interface, and cross-workflow regression evidence;
- shared real-time, perception, tracking, ontology, policy, and tray contracts: consumed without changing their meaning.

## D. escalation conditions

changing the item-resolution rule, one-active-run constraint, shared real-time contracts, tray lifecycle, model contract, ontology, policy semantics, public result meaning, or safety boundary requires a concise change proposal and user decision.
