# verification

> identifies the repository evidence for the implemented tracking package.

**status:** evidence mapped

## A. automated evidence

- motion and tracking lifecycle: `tests/unit/test_kalman.py` and `tests/unit/test_bytetrack.py`;
- duplicate suppression and pipeline integration: `tests/unit/test_boxes.py` and `tests/unit/test_pipeline.py`;
- MOT metrics: `tests/unit/test_mot.py`;
- ordered session evaluation: `tests/integration/test_evaluate_sessions.py`;
- command construction for rendering: `tests/integration/test_cli.py`.

## B. verification commands

```text
python -m pytest -q tests/unit/test_kalman.py tests/unit/test_bytetrack.py tests/unit/test_boxes.py tests/unit/test_pipeline.py tests/unit/test_mot.py
python -m pytest -q tests/integration/test_evaluate_sessions.py tests/integration/test_cli.py
```

## C. limitations

repository tests cover controlled sequences. Claims about dense overlap, long disappearance, camera motion, and visually similar crossings require representative recorded-video evaluation.
