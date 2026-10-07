# product roadmap

> defines the ordered product releases from initial definition to a validated research demonstrator. Each release must produce a usable product increment and objective completion evidence.

## A. release sequence

| order | release | product increment | exit gate |
|---|---|---|---|
| A | R0: product contract | the product boundary, users, workflows, outputs, review states, and success measures are agreed. | the vision, principles, experience, and core use cases are coherent and approved. |
| B | R1: perception baseline | recorded images and video produce instrument detections with confidence and explicit unsupported outcomes. | a versioned dataset, reproducible model, class-level metrics, and failure analysis exist. |
| C | R2: stateful inventory | video observations become a deduplicated inventory that preserves physical item identity across frames. | representative sequences verify tracking, item resolution, counting, and duplicate prevention. |
| D | R3: handling decision support | each resolved item and its context produce a traceable handling outcome or `Needs review`. | tests cover supported policy, missing context, missing policy, uncertainty, and conflicting inputs. |
| E | R4: robot workflow MVP | a continuous stream produces timely per-item handling outputs and incremental inventory updates through a controller-facing interface. | end-to-end tests verify timing, ordering, degraded operation, and safe failure behavior. |
| F | R5: tray workflow MVP | an operator can capture a tray, confirm context, finalize inventory, review outcomes, and export results. | primary, empty, uncertain, and failure scenarios complete through the operator interface. |
| G | R6: edge demonstrator | the core runtime is packaged and deployed on the intended robot edge hardware. | measured latency, throughput, resource use, startup, recovery, and artifact compatibility meet defined targets. |
| H | R7: validated research release | both workflows are reproducible demonstrations with versioned models, policy, interfaces, and reports. | every product claim maps to recorded evidence, and known limitations remain visible. |

## B. release rule

a release is complete only when its product increment works end to end and its exit-gate evidence is recorded. 

## C. conditional backlog

| item | trigger | intended outcome |
|---|---|---|
| reference-based recognition | the validated core workflows need faster class expansion. | determine whether new instrument categories can be added without retraining the deployed model. |
| public-exposure hardening | the demonstrator will be accessible outside its controlled environment. | add the required access, abuse, and data-protection controls. |
| persistent monitoring | the system will operate as a persistent deployment. | expose health, latency, failure, and artifact-version telemetry. |

## D. outside current scope

clinical deployment, sterility assessment, autonomous safety decisions, and safety-critical reconciliation remain outside the product scope.
