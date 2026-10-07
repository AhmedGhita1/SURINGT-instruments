# decision: use COCO as the dataset contract

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

data generation, training, evaluation, and session analysis need one annotation contract. A custom format could match the project exactly but would require custom loaders, validators, and metric integration.

## B. decision

use COCO images, annotations, categories, and absolute `xywh` boxes as the source-data contract. Remap category IDs to contiguous zero-based model IDs at load time while retaining the original COCO IDs for evaluation. Sequence datasets may add identity fields such as `track_id` and physical item identity without changing the base contract.

## C. consequences

standard COCO tooling remains usable and source annotations keep their native identity. Dataset loading must validate category mappings and must not silently rewrite source taxonomy. Project-specific sequence fields require explicit validation.

## D. validation or reversal

validate loaders against representative image and session datasets. Revisit only if a required domain concept cannot be represented as a compatible extension.
