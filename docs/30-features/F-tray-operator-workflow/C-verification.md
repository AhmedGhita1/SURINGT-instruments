# verification

> identifies the repository evidence for the implemented tray operator workflow.

**status:** evidence mapped

## A. automated evidence

- packaged console response: `tests/integration/test_api_health.py`;
- stages, branding, metrics, terminology, context controls, accessibility treatment, result grouping, report content, and API wiring: `tests/unit/test_console_ui.py`;
- API behavior used by the interface: `tests/integration/test_api_sessions.py`.

## B. verification commands

```text
python -m pytest -q tests/unit/test_console_ui.py
python -m pytest -q tests/integration/test_api_health.py tests/integration/test_api_sessions.py
```

## C. limitations

the automated interface checks inspect the packaged HTML and JavaScript but do not execute a real browser, camera, GPU, or accessibility tool. Smooth overlay timing and complete interactive behavior require a recorded browser walkthrough under a declared profile.
