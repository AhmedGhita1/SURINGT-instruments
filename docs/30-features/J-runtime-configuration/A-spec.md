# feature package: runtime configuration defaults

> defines predictable local model and device defaults with explicit environment overrides.

**status:** implemented

**roadmap relationship:** simplifies the existing serving and deployment experience.

## A. outcome

An evaluator or developer can start SURGINT with the standard downloaded model on CUDA without
repeating configuration, while deployments can override either value explicitly.

## B. requirements

- Default the checkpoint to `models/surgint-instruments-rt-detr`.
- Default the inference device to `cuda`.
- Accept `CHECKPOINT` and `DEVICE` as the environment overrides.
- Stop reading the former `SURGINT_CHECKPOINT` and `SURGINT_DEVICE` names.
- Place bundled Docker models at the default checkpoint location and preserve CUDA as the runtime
  default.
- Document the standard model download directory, immutable release-model revision, and both
  overrides.

## C. acceptance

- Settings tests prove both defaults and explicit overrides.
- API, Docker, CI, and README references use the new names and location consistently.
- Focused tests, lint, and relevant repository verification pass.

## D. non-goals

- Downloading a model during API startup.
- Changing model promotion, artifact validation, or the remaining resource-limit variables.
- Claiming real-time CPU performance.
