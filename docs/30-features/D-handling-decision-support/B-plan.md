# implementation plan

> defines the dependency order for ontology-backed handling decisions.

**status:** implemented

## A. foundation

the package consumes resolved perception labels, confidence, tracking identity, and inventory evidence.

## B. approach

1. define immutable observation, context, and decision contracts.
2. package and validate the SURGINT ontology and exact perception-label mapping.
3. define and validate the independent YAML handling policy.
4. implement the ordered decision resolver with explicit review outcomes and provenance.
5. compose session and item context and connect decisions to mutable and finalized inventory.
6. enforce the post-session finalization boundary.

## C. affected boundaries

- `surgint/ontology` and `surgint/policy` artifacts and loaders;
- `surgint/decision` contracts and resolver;
- `surgint/runtime/decision_support.py` and `surgint/runtime/session.py`.

## D. escalation conditions

changing decision precedence, knowledge authority, policy meaning, context fields, or safety presentation requires an approved product or architecture decision.
