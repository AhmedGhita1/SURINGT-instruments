# verification

> identifies the repository evidence for the implemented perception and model-development package.

**status:** evidence mapped

## A. automated evidence

- dataset behavior: `tests/integration/test_dataset.py`;
- model and training: `tests/model/test_detector.py`, `tests/model/test_trainer.py`, and `tests/model/test_pipeline_checkpoint.py`;
- transforms and decoding: `tests/unit/test_transform.py`, `tests/unit/test_decode.py`, and `tests/unit/test_detections.py`;
- evaluation: `tests/integration/test_evaluation.py`, `tests/unit/test_coco_eval.py`, and `tests/unit/test_metrics.py`;
- artifacts and configuration: `tests/integration/test_artifacts.py`, `tests/unit/test_manifest.py`, and `tests/unit/test_config.py`;
- command interfaces: `tests/integration/test_cli.py`.

## B. verification commands

```text
python -m pytest -q tests/unit
python -m pytest -q tests/integration
python -m pytest -q tests/model
```

## C. limitations

the repository consumes prepared COCO data, but `pipelines/build_dataset.py` is only a declared future pipeline. Model-quality claims depend on external datasets, checkpoints, and recorded evaluation results rather than repository tests alone.
