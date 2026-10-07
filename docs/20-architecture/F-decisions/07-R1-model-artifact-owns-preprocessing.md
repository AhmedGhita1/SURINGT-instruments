# decision: make the model artifact authoritative for preprocessing

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

weights can load successfully while runtime configuration applies a different canvas, padding value, scaling rule, or label order. This silently changes the model input distribution or class meaning.

## B. decision

every deployable SURGINT checkpoint carries a validated manifest containing its ordered labels, input size, padding, rescaling, preprocessing contract, source lineage, dataset and training provenance, schema version, and weights digest. Runtime construction reads these values from the artifact, not from the training configuration. Missing or incompatible required metadata prevents loading.

## C. consequences

changing preprocessing or label order creates a new artifact rather than a configuration edit. Runtime startup can detect incompatible or corrupted artifacts. Legacy metadata may be translated during a controlled migration but is not a second authority.

## D. validation or reversal

verify manifest schema, label agreement, required files, and weight digest before inference. Revisit fields as the artifact contract evolves, while preserving one authoritative source.
