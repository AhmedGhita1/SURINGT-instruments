# verification

> defines the evidence required before the robot workflow package can be accepted.

**status:** pending implementation

## A. acceptance profile

record the shared real-time profile, run context, model artifact, frame resolution, offered source rate, item motion, concurrency, timing targets, and overload limits used for robot-workflow verification. R4 makes no robot-edge performance claim.

## B. required evidence

- focused tests for run lifecycle, item resolution, exactly-once emission, ordering, inventory updates, and isolated restart;
- integration tests proving only confirmed detector-backed tracks create robot results;
- API tests for start, state, stop, summary, export, release, invalid input, degraded operation, and critical failure;
- decision tests covering recommendation and every applicable `Needs review` reason;
- a browser walkthrough covering the complete robot-operator flow and visible safety boundary;
- timing results using the shared real-time measurements;
- regression results for existing tray behavior and the relevant full repository checks.

## C. recorded results

no implementation evidence has been recorded.

## D. limitations

record unsupported operating conditions, identity failures, timing limits, and remaining product or deployment gaps after verification.
