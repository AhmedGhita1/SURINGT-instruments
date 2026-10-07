# implementation plan

> defines the service construction around the existing perception, inventory, and decision core.

**status:** implemented

## A. foundation

the package reuses the detector, transform, tracking pipeline, inventory session, and decision resolver without duplicating their semantics.

## B. approach

1. load and validate the model during application startup and expose health states.
2. create a bounded UUID session registry with isolated mutable state and locks.
3. add single-frame image processing and tracked-detection responses.
4. add bounded video decoding, sampling, batching, and atomic session replacement.
5. map validated context into one-shot inventory finalization.
6. add error handling for missing sessions, invalid media, limits, and terminal sessions.

## C. affected boundaries

- `services/api/app.py`, `services/api/schemas.py`, `services/api/sessions.py`, `services/api/settings.py`, and `services/api/video.py`;
- shared detector and runtime session contracts;
- API integration and media-decoding tests.

## D. escalation conditions

changing session lifecycle, exposing partial decisions, adding persistence, supporting multiple workers, or changing public response meaning requires an approved architecture decision.
