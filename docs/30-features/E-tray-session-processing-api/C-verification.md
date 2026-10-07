# verification

> identifies the repository evidence for the implemented tray-session API package.

**status:** evidence mapped

## A. automated evidence

- startup health and packaged console: `tests/integration/test_api_health.py`;
- session creation, deletion, frames, videos, limits, finalization, and terminal-state rejection: `tests/integration/test_api_sessions.py`;
- video decoding and sampling: `tests/integration/test_video_decode.py`;
- runtime finalization lifecycle: `tests/integration/test_session.py`;
- configuration validation: `tests/unit/test_config.py` and API settings coverage in integration tests.

## B. verification commands

```text
python -m pytest -q tests/integration/test_api_health.py tests/integration/test_api_sessions.py tests/integration/test_video_decode.py tests/integration/test_session.py
```

## C. limitations

finalization returns and internally stores the frozen result, but the API does not expose a separate endpoint to retrieve an already finalized result. State is in memory, one process owns inference, and public-client security controls are not implemented.
