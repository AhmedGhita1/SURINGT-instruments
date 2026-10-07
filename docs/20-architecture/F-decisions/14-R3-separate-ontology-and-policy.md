# decision: separate instrument knowledge from handling policy

**status:** accepted

**roadmap milestone:** R3: handling decision support

## A. context

instrument facts describe what an item is, while handling rules describe what an approved workflow says to do under given context. Combining both in OWL or Python would couple domain semantics to operational actions and make policy changes require ontology or code releases.

## B. decision

store instrument facts in the read-only ontology and handling rules in a separately versioned YAML policy artifact. Evaluate policy only after combining a resolved item, ontology facts, and supplied context. Reject malformed, duplicate, or overlapping rules rather than relying on file order. Use stable action IDs with operator explanations.

## C. consequences

knowledge and operational policy can evolve, review, and test independently. Runtime releases must pin compatible ontology and policy versions. The boundary requires explicit mappings and compatibility validation between artifacts.

## D. validation or reversal

test every approved rule, every intentionally uncovered combination, and overlap rejection. Merge the stores only if future governance establishes one authority and the combined representation remains equally traceable.
