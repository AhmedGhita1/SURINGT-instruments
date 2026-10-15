# implementation plan

> defines the checkpoints that move real-time inference to one analysis loop with live overlays for live and recorded video.

**status:** proposed

**branch:** `feat/rt-infer`

## A. foundation

The branch already provides timing instrumentation, temporal frame and result metadata, elapsed-time tracking, bounded live scheduling, and reporting of recorded files that stop decoding. On the local workstation GPU, one round trip takes about 50 ms at 1080p and about 150 ms at 4K, so the server is not the bottleneck at normal resolutions.

The camera uses a latest-frame scheduler with an overwrite slot, generation checks, result suppression, about 30 counters, and a display-prediction request on every drawn frame. Recorded video uses a simple loop: one request in flight and the latest result drawn on each frame. This plan makes the simple loop the only loop and removes what only the old camera design needed.

## B. approach

### B.1 one analysis loop in the page

- **outcome:** camera and recorded video share one loop. It selects a frame every 0.2 seconds of source time, keeps one request in flight, skips busy selections for live video, pauses recorded playback until the result returns, draws the latest result, and hides stale live overlays. It ignores results from an earlier source or that arrive after stop.
- **removes:** the latest-frame scheduler, display-prediction requests, the generation and suppression machinery beyond that one source check, and the counters that only described them. A small timing summary stays on `window.surgintTiming`.
- **affected:** `services/api/static/index.html`, `tests/unit/test_console_ui.py`.
- **verification:** console tests describe the new loop. Chrome runs with a recorded 1080p file and a fake camera fed from a video show one request at a time and counted skipped live selections. Two runs of the 1080p file analyze identical timestamps. A result that arrives after a discard does not change the new scan.
- **commit:** `refactor: share one analysis loop for camera and video`

### B.2 native video with a box overlay

- **outcome:** the stage shows the video element itself, and a transparent canvas redraws boxes only when a result arrives, scaled to the displayed size.
- **affected:** `services/api/static/index.html`, `tests/unit/test_console_ui.py`.
- **verification:** the 4K Magdeburg file plays with almost no dropped frames, and two runs analyze identical timestamps. Boxes align with objects at 4K and 720p. Capture, review, and finalize states look unchanged.
- **commit:** `perf: draw overlays over native video playback`

### B.3 one frame per session on the server

- **outcome:** the frame endpoint rejects a frame with HTTP 429 when its session already has one processing, instead of waiting on the session lock. The page counts a rejection as a skipped selection. The session limit then bounds total work.
- **affected:** `services/api/app.py`, its tests, `services/api/static/index.html`.
- **verification:** an API test sends two concurrent frames to one session and gets one result and one 429. A browser run shows rejections counted as skips.
- **commit:** `fix: reject concurrent frames for a busy session`

### B.4 remove display-time prediction from the server

- **outcome:** the display-predictions endpoint, its schemas, the session display-timestamp check, and the pipeline and tracker display projection are deleted. Elapsed-time tracking stays.
- **affected:** `services/api/app.py`, `services/api/schemas.py`, `services/api/sessions.py`, `surgint/runtime/pipeline.py`, `surgint/runtime/bytetrack.py`, their tests, and the latest-frame simulation in `pipelines/measure_realtime.py`.
- **verification:** ruff, unit, integration, and model suites pass. Variable-rate tracking tests pass unchanged.
- **commit:** `refactor: remove display-time track prediction`

### B.5 evaluation and current evidence

- **outcome:** the RTI-07 profile is measured against its declared targets, tray finalization regressions pass, and `C-verification.md` is rewritten to current evidence only.
- **affected:** `docs/30-features/H-real-time-inference/`.
- **verification:** the report lists hardware, model, sources, configuration, metrics, limits, and the pass or fail result.
- **commit:** `docs: record real-time inference evaluation`

After the last checkpoint, a fresh reviewer checks the real-time inference commits on the branch against the spec. The runtime configuration commits are already reviewed.

## C. affected boundaries

- browser console: one analysis loop and overlay rendering;
- `services/api`: frame endpoint rejects concurrent frames per session, display-predictions endpoint removed;
- `surgint/runtime`: display projection removed, elapsed-time tracking unchanged;
- evaluation tooling and feature documentation.

## D. escalation conditions

- two runs of the same 4K file still analyze different timestamps after checkpoint B.2;
- live analysis falls below 5 selections per second at 720p on the local workstation GPU;
- removing display projection changes tracking or inventory results;
- the Hugging Face Space profile must meet the same limits as the local profile;
- any change to the frame endpoint's contract other than the busy rejection.
