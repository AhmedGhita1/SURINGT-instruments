# product vision

SURGINT Instruments is a stateful, real-time perception and decision-support system for surgical-instrument processing. It observes instruments, builds an inventory, and connects resolved surgical instruments to handling/procedure decisions.

## A. purpose

The project demonstrates end-to-end AI systems engineering across data, models, real-time inference, runtime state, APIs, deployment, and evaluation. Product claims must remain measurable and suitable for a credible engineering demonstration.

## B. product problem

Instrument processing requires more than frame-level recognition. A useful system must preserve physical identity, avoid duplicate inventory entries, resolve each item at the correct time, communicate uncertainty, and keep perception separate from handling decisions.

## C. supported workflows

### C.1 continuous robot operation

This is the primary workflow. A robot processes a continuous video stream and handles instruments sequentially, usually one item at a time. SURGINT provides immediate perception and handling outputs for each resolved physical item, updates the inventory incrementally, and keeps the current state available to the supervising operator.


### C.2 instrument-tray inventory

This is the secondary workflow. An operator opens a live stream or recorded video, observes synchronized detections and tracks, confirms context, then receives a finalized inventory, handling decision outcomes, and exportable report.

## D. users and consumers

- The robot controller consumes per-item decisions.
- The robot operator supervises the run and inventory.
- The tray operator or evaluator captures, finalizes, and reviews a tray session.
- Researchers and engineers evaluate system quality and limitations.

## E. product boundary

SURGINT Instruments is a research prototype. It is not clinically validated and must not be used for patient care, clinical decisions, sterility assessment, autonomous safety decisions, or safety-critical instrument accounting.

## F. success

Success means each workflow produces the right output at the right time, unresolved items require review, results are traceable to evidence and policy, and measured limitations are stated as clearly as capabilities.
