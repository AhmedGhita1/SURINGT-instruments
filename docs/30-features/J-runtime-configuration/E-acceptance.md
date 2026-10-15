# acceptance

> records the user's final decision after implementation and review.

**status:** accepted with follow-ups

The user accepted the runtime configuration defaults on 2026-10-15, based on the passing independent review and the recorded verification.

Follow-ups:

- Publish a new image tag and reference it in the README before presenting the new Docker configuration as released. The README quick start still pulls `1.1.0`, which predates this configuration contract.
- Confirm in the pull-request CI run that the two TestClient-based API test files pass. They hang on the development host and have not yet run in CI.
