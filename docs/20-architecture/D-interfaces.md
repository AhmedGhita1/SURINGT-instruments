# interfaces

> defines the stable information exchanged between core components, workflow coordinators, and operator interfaces without prescribing transport or code structure.

## A. core contracts

| contract | producer | required information | primary consumers |
|---|---|---|---|
| frame input | input adapter | run or session identity, sequence, source timestamp, frame data, and source metadata | perception and workflow coordinator |
| observation | perception | frame identity, bounding box, predicted class, confidence, and perception artifact version | tracking and operator overlay |
| tracked observation | tracking | observation data, stable track identity, and track state | item resolution, inventory, and operator overlay |
| resolved item | item resolution | run identity, stable item identity, resolved class, confidence, evidence range, resolution time, and resolution status | inventory and decision support |
| operator context | operator interface | workflow stage, use state, contamination state, and approved item-level overrides where applicable | decision support |
| handling outcome | decision support | item identity, outcome, optional guidance, reason, matched rule or review reason, and knowledge and policy versions | workflow coordinator and operator interface |
| inventory update | inventory | run identity, item identity, class, current count, resolution time, and associated handling outcome | robot coordinator and robot-operator interface |
| finalized result | tray coordinator | frozen inventory, handling outcomes, unresolved items, context, artifact versions, and completion state | tray interface and export |
| workflow status | workflow coordinator | workflow identity, state, timing or backlog condition, and actionable failure details | operator interface and operations |

## B. robot processing algorithm

```text
algorithm run_robot(stream, context, release_set):
    validate(release_set)
    run := create_isolated_run()
    set_state(run, READY)

    try:
        set_state(run, ACTIVE)

        while robot_operator_has_not_stopped(run):
            frame := receive_next_ordered_frame(stream)

            if processing_limit_would_be_exceeded(frame):
                apply_declared_overload_behavior()
                set_state(run, DEGRADED)

            observations := perceive(frame)
            tracks := update_tracks(observations)
            new_items := resolve_new_physical_items(tracks)

            for item in new_items:
                if inventory.already_contains(item.identity):
                    continue

                outcome := decide(item, context, release_set)
                inventory_update := inventory.add_once(item)
                publish_atomically(item, outcome, inventory_update)

        set_state(run, STOPPED)
        return export_final_summary(run)

    on critical_input_or_runtime_failure as error:
        stop_new_item_resolution()
        set_state(run, FAILED, error)
        notify_robot_operator(error)
```

## C. robot workflow contract

the robot-operator interface shall support starting and stopping a run and observing `ready`, `active`, `degraded`, `failed`, and `stopped` states where applicable. During an active run it shall expose the latest resolved item, handling outcome, incremental inventory, unresolved items, and timing status.

per-item outputs shall be ordered by resolution time and identified so retries or repeated delivery cannot create duplicate inventory entries.

## D. tray processing algorithm

```text
algorithm capture_tray(source, release_set):
    validate(release_set)
    session := create_isolated_session(state = CAPTURING)

    while tray_operator_is_capturing(session):
        frame := receive_next_ordered_frame(source)
        observations := perceive(frame)
        tracks := update_tracks(observations)
        session.draft_inventory.observe(tracks)
        publish_synchronized_overlay(frame, tracks)

    set_state(session, READY_TO_FINALIZE)
    return session.identity

algorithm finalize_tray(session, context):
    require_state(session, READY_TO_FINALIZE)
    validate_required_context(context)

    frozen_inventory := session.draft_inventory.freeze()
    outcomes := []

    for entry in frozen_inventory:
        outcomes.append(decide(entry, context, session.release_set))

    result := freeze_result(frozen_inventory, outcomes)
    set_state(session, FINALIZED)
    return result

algorithm get_finalized_tray_result(session):
    require_state(session, FINALIZED)
    return the_same_frozen_result_without_recomputation()
```

## E. tray workflow contract

the tray interface shall support creating a session, submitting live or recorded frames, observing synchronized detections and tracks, finishing or discarding capture, providing context, finalizing once, and retrieving or exporting the frozen result.

after finalization, perception and inventory mutation shall be rejected. Repeated result retrieval shall return the same finalized result.

## F. workflow states

| workflow | non-terminal states | terminal states |
|---|---|---|
| robot run | `ready`, `active`, `degraded` | `stopped`, `failed` |
| tray session | `capturing`, `ready-to-finalize` | `finalized`, `discarded`, `failed` |

state changes shall be explicit. A failed or terminal workflow shall not resume by silently reusing its state.

## G. compatibility rules

- every external or persisted contract shall declare a schema version.
- additive optional fields may remain compatible within a schema version; removed fields, changed meaning, or new mandatory fields require a new version.
- consumers shall reject unsupported mandatory versions before producing results.
- identifiers shall be unique within their documented scope, and timestamps shall state their source and ordering semantics.
- exported results shall include the release-set versions needed for traceability.
