# feature package: handling decision support

> defines how resolved instrument observations, domain knowledge, operator context, and handling policy produce traceable outcomes.

**status:** implemented

**roadmap relationship:** R3: handling decision support

## A. outcome

each supported resolved instrument can produce an explained handling recommendation or a specific review outcome without embedding handling rules in perception code.

## B. sub-features

### B.1 DEC-01: versioned instrument ontology

**definition:** Stores the supported instrument concepts and asserted facts required by handling decisions.

**specification:**

- Load the packaged SURGINT ontology read-only and validate its identity, version, labels, and controlled values.
- Represent absent facts as unknown rather than inventing defaults.

**verification:** Ontology loading and validation tests cover identity, schema, catalog coverage, duplicates, and invalid facts.

### B.2 DEC-02: perception-to-knowledge mapping

**definition:** Resolves a perception label to one ontology concept and its asserted instrument facts.

**specification:**

- Join through the exact machine-facing `perceptionLabel` rather than display text or model class position.
- Preserve unsupported labels as explicit outcomes.

**verification:** Mapping tests cover complete label coverage, display-label independence, ordering, and duplicate rejection.

### B.3 DEC-03: versioned handling policy

**definition:** Stores handling rules separately from instrument knowledge and application code.

**specification:**

- Load typed YAML rules with stable identifiers, conditions, actions, and operator explanations.
- Reject unsupported schemas, duplicate rule identifiers, invalid values, and overlapping matches.

**verification:** Policy loader and evaluator tests cover valid matches, missing facts, uncovered facts, malformed rules, and overlap rejection.

### B.4 DEC-04: ordered decision resolution

**definition:** Combines an observation, instrument facts, context, and policy into one immutable decision.

**specification:**

- Evaluate unsupported labels, confidence, knowledge, context, and policy through the accepted precedence order.
- Return typed review outcomes without actions when a justified recommendation cannot be produced.

**verification:** Resolver tests cover every outcome, precedence, conflicts, internal failure, explanations, and artifact provenance.

### B.5 DEC-05: session and item context

**definition:** Applies shared workflow facts and optional item-specific facts without mutating knowledge or policy.

**specification:**

- Validate workflow stage, use state, contamination state, product identity, and lifecycle values.
- Detect conflicting lifecycle information and require review rather than selecting one source silently.

**verification:** Context and integration tests cover composition, missing fields, overrides, conflicts, and absent inventory items.

### B.6 DEC-06: finalized inventory decisions

**definition:** Produces one immutable decision for each finalized class-level inventory entry.

**specification:**

- Resolve the finalized inventory once and preserve its class, count, representative evidence, and decision together.
- Expose no partial decisions before session finalization.

**verification:** Session tests cover one-shot finalization, immutable results, failed correction attempts, and complete inventory resolution.

## C. shared constraints

- Preserve ADRs `13` through `15` and requirements `FR-006` through `FR-008`, `QR-203`, and `SR-101` through `SR-201`.
- Instrument knowledge and handling policy remain separately versioned and read-only at runtime.
- Only `recommendation` may contain an action; every other outcome is presented as `Needs review` to operators.

## D. package acceptance

- supported facts and complete context select one deterministic handling rule with an explanation.
- unsupported, uncertain, incomplete, uncovered, conflicting, and failed cases produce the correct review reason without an action.
- every outcome carries the model, ontology, and policy provenance needed for traceability.
- finalized inventory decisions are immutable and unavailable before finalization.

## E. non-goals

- clinical decisions, sterility assessment, or autonomous safety decisions;
- robot motion or execution commands;
- OWL reasoning beyond direct asserted-fact extraction;
- runtime editing of ontology or policy;
- automatic policy generation or approval.
