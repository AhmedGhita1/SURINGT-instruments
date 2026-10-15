# verification

> records checks and limitations for the runtime configuration defaults.

**status:** verified

## A. required evidence

- Settings default and environment-override tests.
- API health and packaging tests.
- Dockerfile and CI configuration inspection.
- Repository lint, unit, integration, and model tests.

## B. recorded results

- `python -m ruff check services surgint tests`: passed.
- `python -m pytest -q tests/unit`: 160 passed.
- Non-API integration groups: 90 passed.
- `python -m pytest -q tests/model`: 10 passed.
- Focused console and video tests: 23 passed.
- `git diff --check`: passed.
- `docker buildx build --check --target production ...`: passed with no warnings.
- `docker build --target ci -t surgint:ci .`: passed; the image validated the checkpoint at
  `/app/models/surgint-instruments-rt-detr`.
- The image started with `--gpus all` and no device override. Readiness returned HTTP 200,
  `torch.cuda.is_available()` returned `True`, and PyTorch identified the device as an NVIDIA
  GeForce RTX 4090.
- `PYTHON=python3 bash docker/smoke.sh`: passed health, readiness, session, frame inference,
  finalization, deletion, and two-frame video inference checks against the GPU container.
- Static reference inspection found no runtime use of `SURGINT_CHECKPOINT`, `SURGINT_DEVICE`, or
  `/app/model`.

## C. limitations

The two TestClient-based API files could not complete directly on this host. A request through a
minimal FastAPI `TestClient` hangs with the repository-pinned FastAPI, Starlette, and `httpx2`
versions, independently of SURGINT. The GPU container smoke test exercised the corresponding live
API paths successfully. The runtime logged that its optional custom CUDA extension was unavailable
and used the existing PyTorch CUDA fallback; inference still completed successfully on the GPU.
