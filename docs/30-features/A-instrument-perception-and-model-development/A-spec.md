# feature package: instrument perception and model development

> defines the data, model, training, inference, evaluation, and artifact capabilities that establish the perception baseline.

**status:** implemented

**roadmap relationship:** R1: perception baseline

## A. outcome

researchers can train, evaluate, save, load, and run a closed-set surgical-instrument detector through one reproducible perception contract.

## B. sub-features

### B.1 PER-01: COCO dataset consumption

**definition:** Loads versioned COCO annotations and images for detection training and evaluation.

**specification:**

- Preserve the declared category mapping while exposing contiguous model class identifiers.
- Return RGB frames and frame-space `xyxy` boxes through the shared dataset contract.

**verification:** Dataset tests cover category mapping, samples, task validation, and batching.

### B.2 PER-02: canonical frame transformation

**definition:** Converts input frames into model tensors and maps predicted boxes back into original-frame coordinates.

**specification:**

- Use the same resize, padding, normalization, and coordinate rules in training and inference.
- Preserve non-square geometry and clip returned boxes to valid frame bounds.

**verification:** Transform tests round-trip known boxes and validate pixel values, padding, and output geometry.

### B.3 PER-03: closed-set RT-DETR detection

**definition:** Wraps the pretrained RT-DETR model and decodes its queries into immutable instrument detections.

**specification:**

- Produce aligned boxes, scores, and class identifiers with one selected class per query.
- Support empty results, confidence filtering, batching, CPU inference, and mixed precision on CUDA.

**verification:** Detector, decode, and pipeline tests cover construction, inference, filtering, batching, and empty frames.

### B.4 PER-04: configurable model training

**definition:** Fine-tunes the detector using an explicit PyTorch training and validation loop.

**specification:**

- Apply differential learning rates, warmup and cosine scheduling, gradient clipping, and frozen BatchNorm statistics.
- Preserve resumable training state separately from the checkpoint selected by validation metrics.

**verification:** Trainer tests cover setup, epochs, validation, checkpoint selection, resume state, and the full training loop.

### B.5 PER-05: detection inference and evaluation

**definition:** Runs the trained model on images and measures detection quality using the same runtime contracts.

**specification:**

- Provide an image inference command that reports detections and writes an annotated result.
- Report COCO metrics and class-sensitive detection behavior on a declared evaluation split.

**verification:** CLI and evaluation tests cover command construction, prediction conversion, thresholds, and metric computation.

### B.6 PER-06: self-describing model artifact

**definition:** Packages weights with the labels, preprocessing parameters, provenance, schema version, and integrity data required by runtime consumers.

**specification:**

- Reject unsupported schemas or weights that do not match the recorded digest.
- Record the training data, configuration, environment, and pinned pretrained-model revision used to create the artifact.

**verification:** Manifest and artifact tests cover round trips, integrity rejection, provenance, and checkpoint compatibility.

## C. shared constraints

- Preserve ADRs `01` through `09` and requirements `FR-003`, `OR-002`, `QR-101`, and `QR-302`.
- Model preprocessing and label meaning belong to the artifact, not deployment-specific code.
- Training and runtime dependencies remain separable.

## D. package acceptance

- a configured training run produces resumable and selected checkpoints with reproducible metadata.
- a saved checkpoint reloads and produces frame-space detections through the runtime pipeline and image CLI.
- detection evaluation reports the configured metrics and class-level failure evidence.
- incompatible or corrupted model artifacts fail before inference.

## E. non-goals

- data collection, synthetic-scene generation, annotation, or a completed immutable-dataset publishing pipeline;
- open-vocabulary or reference-based recognition;
- automatic retraining or model promotion;
- tracking, inventory, handling decisions, or serving interfaces.
