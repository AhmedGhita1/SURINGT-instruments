# decision: maintain a SURGINT-specific read-only ontology

**status:** accepted

**roadmap milestone:** R3: handling decision support

## A. context

existing external ontologies did not cover the complete perception taxonomy, especially containers and consumables. The model label vocabulary and domain concepts must remain aligned, while runtime inference must not mutate shared knowledge.

## B. decision

maintain a versioned SURGINT ontology covering supported perception concepts and required instrument facts. Join model labels to concepts using an exact machine-facing `perceptionLabel`, not a display label. Load and validate the ontology as a read-only artifact. Extract asserted facts directly rather than introducing an OWL reasoner for the current flat catalog.

## C. consequences

the domain vocabulary can evolve with the product taxonomy and remains independent of model class IDs. Missing concepts become explicit unsupported outcomes. Direct extraction is fast and transparent but does not infer facts through deeper semantic axioms.

## D. validation or reversal

verify unique perception labels, valid value ranges, ontology version identity, and model-label coverage. Introduce a reasoner only when approved knowledge requirements depend on inference that direct extraction cannot express clearly.
