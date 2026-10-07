# verification

> identifies the repository evidence for the implemented handling decision-support package.

**status:** evidence mapped

## A. automated evidence

- ontology identity, mapping, and validation: `tests/integration/test_ontology_loader.py`, `tests/integration/test_ontology_mapping.py`, and `tests/integration/test_ontology_validation.py`;
- policy loading and evaluation: `tests/integration/test_policy_loader.py` and `tests/integration/test_policy_evaluator.py`;
- decision contracts and ordered outcomes: `tests/unit/test_decision_models.py` and `tests/integration/test_decision_resolver.py`;
- inventory integration and finalization lifecycle: `tests/integration/test_decision_support.py` and `tests/integration/test_session.py`;
- packaged artifact presence: `tests/integration/test_packaging.py`.

## B. verification commands

```text
python -m pytest -q tests/unit/test_decision_models.py
python -m pytest -q tests/integration/test_ontology_loader.py tests/integration/test_ontology_mapping.py tests/integration/test_ontology_validation.py
python -m pytest -q tests/integration/test_policy_loader.py tests/integration/test_policy_evaluator.py tests/integration/test_decision_resolver.py tests/integration/test_decision_support.py tests/integration/test_session.py
```

## C. limitations

the ontology and policy cover the current catalog and rules only. Correct software behavior does not establish clinical validity or completeness of domain policy.
