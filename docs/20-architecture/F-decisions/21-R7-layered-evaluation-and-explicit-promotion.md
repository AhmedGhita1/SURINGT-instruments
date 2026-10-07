# decision: evaluate by layer and promote complete release sets explicitly

**status:** accepted

**roadmap milestone:** R7: validated research release

## A. context

detection mAP alone cannot establish tracking identity, inventory correctness, decision behavior, or runtime suitability. Independently selecting the latest model, ontology, policy, configuration, and schemas can also create combinations that were never evaluated together.

## B. decision

maintain separate but connected evidence for:

- detection using the application postprocessing path and class-level COCO metrics;
- tracking using sequence identity metrics and reset state per session;
- inventory using physical item truth, count error, duplicates, and unresolved outcomes;
- decision support using every outcome, rule, missing-input, and conflict path;
- deployment using latency, throughput, backlog, resource, startup, and recovery measurements.

promote only an explicitly approved release set that pins compatible application code, model artifact, dataset evidence, instrument knowledge, handling policy, configuration, and interface schemas. Keep weak classes and unsupported conditions visible.

## C. consequences

each product claim maps to relevant evidence and rollback can select a previously accepted complete set. Promotion requires more than copying the best checkpoint, and evidence must be regenerated when a component change invalidates a claimed result.

## D. validation or reversal

verify the release set against its acceptance profile and reproduce its recorded evaluation. Automate gates only after the evidence and approval semantics remain visible and reviewable.
