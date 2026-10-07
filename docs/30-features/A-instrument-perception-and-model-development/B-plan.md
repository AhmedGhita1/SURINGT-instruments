# implementation plan

> defines the dependency order used to establish the perception baseline.

**status:** implemented

## A. foundation

the package starts from curated COCO-format data and a pinned pretrained RT-DETR revision.

## B. approach

1. establish the frame, annotation, label, and configuration contracts.
2. implement one transform for training and inference, including inverse box mapping.
3. wrap RT-DETR and define immutable decoded detections.
4. implement training, validation, checkpoint selection, and resume state.
5. add image inference and COCO evaluation entry points.
6. make the saved model artifact own preprocessing, labels, provenance, and integrity validation.

## C. affected boundaries

- `surgint/dataset`, `surgint/model`, and `surgint/engine`;
- `pipelines/train.py` and `pipelines/evaluate.py`;
- `surgint/cli/infer.py`, configuration, and model artifacts.

## D. escalation conditions

changing the class vocabulary, data split, base model family, metric definitions, or artifact schema requires an approved product or architecture decision.
