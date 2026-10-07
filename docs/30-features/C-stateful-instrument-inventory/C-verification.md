# verification

> identifies the repository evidence for the implemented stateful inventory package.

**status:** evidence mapped

## A. automated evidence

- runtime accumulation, counting, finalization, reset, and validation: `tests/unit/test_runtime_inventory.py`;
- inventory metrics and invalid evaluation data: `tests/unit/test_evaluation_inventory.py`;
- session-level integration with tracking: `tests/integration/test_evaluate_sessions.py`;
- inventory and decision-support integration: `tests/integration/test_decision_support.py` and `tests/integration/test_session.py`.

## B. verification commands

```text
python -m pytest -q tests/unit/test_runtime_inventory.py tests/unit/test_evaluation_inventory.py
python -m pytest -q tests/integration/test_evaluate_sessions.py tests/integration/test_decision_support.py tests/integration/test_session.py
```

## C. limitations

the final count heuristic reduces track-fragment overcounting but cannot recover every physical identity. It may undercount same-class items that are never visible together.
