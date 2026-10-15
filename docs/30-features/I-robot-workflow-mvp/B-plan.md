# implementation plan

> defines the checkpoints that add robot-run coordination fed by ROS images on top of the shared real-time runtime.

**status:** proposed

**branch:** `feat/robot-deploy`

## A. foundation

`H-real-time-inference` provides the frame endpoint with temporal identity, elapsed-time tracking, one frame per session with HTTP 429 for a busy session, and the workflow-neutral selection rule. The model, tracking, inventory, ontology, policy, and decision contracts already exist. The tray lifecycle remains separate and unchanged.

Images arrive from the robot's ROS node. A small bridge node outside the SURGINT service turns them into frame requests, so SURGINT itself stays free of ROS code.

## B. approach

### B.1 robot-run coordination

- **outcome:** immutable item-result, inventory-entry, run-summary, and status contracts, plus a coordinator that resolves each newly confirmed track once through existing decision support and publishes its result with its inventory entry.
- **affected:** `surgint/runtime`, `tests/unit`.
- **verification:** domain tests cover exactly-once emission, ordered simultaneous confirmations, `Needs review` without an action, frozen item fields, and the degraded rule.
- **commit:** `feat: add robot-run coordination`

### B.2 robot-run API

- **outcome:** a registry with one active run that reuses the shared detector, and endpoints for start, frame, state, stop, summary, export, and release. The frame endpoint follows the shared frame contract and busy rejection.
- **affected:** `services/api`, `tests`.
- **verification:** API tests cover lifecycle, active-run conflict, HTTP 429 for a busy run, degraded and failed states, rejected input after stop, and isolated restart. Tray tests pass unchanged.
- **commit:** `feat: add robot-run API`

### B.3 robot-operator page

- **outcome:** a separate page shows the latest resolved item, outcome, append-only inventory, unresolved confirmed evidence, timing condition, and failures, then the stop summary and JSON export. It exposes no robot commands.
- **affected:** `services/api/static`, its tests.
- **verification:** a browser walkthrough with frames posted from the 1080p demo straight to the frame endpoint covers start, live results, review outcomes, degraded state, stop, summary, export, and failure.
- **commit:** `feat: add robot-operator page`

### B.4 ROS image bridge

- **outcome:** a small ROS node subscribes to the image topic, applies the selection rule by header timestamp, and posts selected images to the robot-run frame endpoint. Publishing results back into ROS is added only if the open decision requires it.
- **affected:** a new bridge directory outside the `services` and `surgint` packages, with its own tests.
- **verification:** the 1080p demo replayed as ROS images reaches the run with selections on the 0.2-second grid, one request in flight, and counted skips.
- **blocked until decided:** the ROS version, the image topic and message type, and whether results go back into ROS.
- **commit:** `feat: add ROS image bridge`

### B.5 evaluation and evidence

- **outcome:** the ROB-07 profile is measured through the ROS bridge on the local workstation GPU, tray regressions pass, and `C-verification.md` records current evidence only.
- **affected:** `docs/30-features/I-robot-workflow-mvp/`.
- **verification:** the report lists hardware, model, input, configuration, metrics, and the pass or fail result.
- **commit:** `docs: record robot workflow evaluation`

After the last checkpoint, a fresh reviewer checks the package against the spec.

## C. affected boundaries

- `surgint/runtime`: robot-run coordination and immutable robot result contracts;
- `services/api`: robot-run registry, schemas, endpoints, and operator page;
- a separate ROS bridge node;
- `tests`: lifecycle, exactly-once behavior, decision, failure, interface, bridge, and tray regression evidence;
- shared real-time, perception, tracking, ontology, policy, and tray contracts: consumed without changing their meaning.

## D. escalation conditions

- any open ROS decision is still undecided when B.4 starts;
- the bridge cannot work without ROS code inside the SURGINT service;
- results must go back into ROS in a way that changes the result contract;
- changing the item-resolution rule, one-active-run constraint, shared real-time contracts, tray lifecycle, model contract, ontology, policy semantics, public result meaning, or safety boundary.
