# decision: share the core while separating workflow coordination

**status:** accepted

**roadmap milestone:** R4: robot workflow MVP

## A. context

continuous robot operation and tray inventory use the same perception, identity, inventory, knowledge, and policy concepts but require different timing. A single generic session lifecycle would either delay robot results until finalization or make tray decisions provisional. Separate full systems would duplicate core behavior and allow semantics to drift.

## B. decision

share stable core contracts for frames, observations, tracks, resolved items, inventory, context, and handling outcomes. Place timing and lifecycle behavior in separate robot-run and tray-session coordinators. The robot coordinator publishes one handling outcome and inventory update per resolved item during the run. The tray coordinator collects observations and publishes inventory and outcomes only after finalization.

## C. consequences

model, tracking, knowledge, and policy improvements can serve both workflows. Each coordinator remains simple and explicit instead of accumulating workflow mode flags. Shared contracts must preserve the same domain meaning across edge and cloud packaging.

## D. validation or reversal

run end-to-end contract tests for both workflows against the same core components. Split a core component only if the workflows require incompatible semantics rather than different orchestration.
