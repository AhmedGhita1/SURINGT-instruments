# verification

> records the current evidence for one analysis loop, live overlays, and the RTI-07 evaluation on the local workstation GPU.

**status:** implementation complete, awaiting independent review

**result:** pass. Every RTI-07 target at 720p and 1080p is met on the local workstation GPU. 4K 60 fps recorded video is not repeatable across runs (section F).

The raw report is `evaluation-workstation-rtx4090.json`.

## A. evaluation profile

- **deployment:** the `production` target of the repository `Dockerfile`, built from commit `7e1f306` and run on the workstation with `docker run --rm --gpus all -p 127.0.0.1:7862:7860`. One session at a time.
- **browser:** Google Chrome 151.0.7922.71, headless on the same machine, with `--use-angle=vulkan --enable-features=Vulkan --ignore-gpu-blocklist`, driven by a throwaway Playwright script outside the repository.
- **hardware:** NVIDIA GeForce RTX 4090 24 GB, driver 560.35.05; AMD Ryzen Threadripper PRO 7955WX, 16 cores and 32 threads; Ubuntu 22.04.5, kernel 6.8.0.
- **model:** `AhmedGhita/surgint-instruments-rt-detr` at revision `bf22ea6`, RT-DETR r18vd, weights `sha256:ef6c387c…`, training run `fair-raven_20260917_1701`, dataset `production_v5`, input 1024 by 576.
- **configuration:** analysis interval 0.2 s, overlay age limit 0.4 s, JPEG quality 0.9, class-agnostic NMS at 0.7, container defaults otherwise.
- **sources:**
  - 720p camera: Chrome's fake capture device fed from the first 30 s of `data/synthetic/demos/demo.mp4`, scaled to 1280 by 720 at 30 fps. Each run lasts 30 s.
  - 1080p synthetic demo: `data/synthetic/demos/demo.mp4`, 1920 by 1080 at 24 fps, 64 s.
  - 4K Magdeburg: the first 30 s of `data/real/magdeburg/magdeburg_20260910_video_01.mp4`, 3840 by 2160 at 60 fps, displayed in portrait.
- **quality ground truth:** the 16 annotated `production_v5` eval sessions, 1280 by 720 at 10 fps, 60 s each.

## B. RTI-07 loop results

Two runs per source. Paired values show run 1 and run 2.

| metric | 720p camera | 1080p demo | 4K Magdeburg | target at 720p and 1080p | result |
|---|---|---|---|---|---|
| grid selections analyzed | 150 of 150, twice | 320 of 320, twice | 150 of 150, twice | | |
| analyses per second | 5.0 | 5.0 | 5.0 | at least 5 | pass |
| p50 capture to result, ms | 38.0 / 35.9 | 48.3 / 52.3 | 174.8 / 178.9 | | |
| p95 capture to result, ms | 42.7 / 40.7 | 52.7 / 57.9 | 185.6 / 216.5 | at most 200 | pass |
| maximum live overlay age, ms | 266.9 / 266.9 | | | at most 400 | pass |
| stale overlay frames | 0 / 0 | 0 / 0 | 0 / 0 | | |
| skipped selections | 0 / 0 | 0 / 0 | 0 / 0 | | |
| paused playback, s | | 0 / 0 | 0 / 0.01 | | |
| frame requests in flight, maximum | 1 / 1 | 1 / 1 | 1 / 1 | no queued frames | pass |
| dropped video frames | | 0 of 1,535 / 0 of 1,536 | 1 of 1,784 / 5 of 1,782 | | |
| identical analyzed timestamps | | yes | no, 13 of 150 differ | | |
| same final inventory | | yes | no | | |

- Capture to result runs from the start of frame capture in the page to the parsed response.
- Live overlay age is the time since capture of the result on screen, sampled on every displayed frame.
- Analyses per second equals the 0.2 s grid rate because no selection was skipped.
- Requests in flight come from the browser's network events, not from the page's own counters.

## C. tracking and inventory quality

The three RTI-07 sources have no frame annotations. Quality is therefore measured with `pipelines.measure_realtime`, in process on CUDA, with the same server code and model, on the 16 annotated eval sessions at the 0.2 s grid. That is 300 analyses per session and 4,800 in total. The loop analyzed every grid selection at 720p and 1080p on this profile, so these are the frames it would analyze. There is no target.

| metric | value |
|---|---|
| pooled MOTA | 0.629 |
| mean IDF1 | 0.696 |
| identity switches | 477 in total, median 30.5 per session |
| confirmation delay | 0.8 s in all 16 sessions, on the fifth observation |
| inventory absolute error | mean 6.75 items per session, against a mean of 21.25 ground-truth items |
| class exact-match rate | mean 0.644 |
| session exact-match rate | 1 of 16 |

These numbers describe the current model and tracker. This package did not change detection, tracking, or inventory (section D, RTI-03).

## D. behavior and contract evidence

Browser checks ran against the deployed container unless noted.

- **RTI-01 temporal identity:** `tests/unit/test_temporal.py` and the identity tests in `tests/integration/test_api_sessions.py` cover round trip, all-or-none metadata, source changes, non-monotonic sequence and time, dimension mismatch, and per-session isolation.
- **RTI-02 one loop:**
  - Every run had at most one frame request in flight.
  - With 500 ms added to each response, the camera counted 20 skipped selections.
  - A copy of every third page frame was sent to the server first. The page's own request then got HTTP 429 all 24 times, the page counted 24 skips, and the scan continued.
  - `test_concurrent_frame_for_a_busy_session_is_rejected_not_queued` returns one 200 and one 429. It fails against the previous endpoint, which made the second frame wait.
  - A response held back from a discarded recorded scan was released during a new camera scan and did not enter it.
- **RTI-03 elapsed-time tracking:**
  - Covered by `test_confirmation_requires_hits_and_elapsed_source_time`, `test_loss_uses_elapsed_source_time_not_update_count`, `test_timestamped_replay_is_deterministic`, `test_tracker_rejects_non_monotonic_source_time_without_mutation`, and `test_predict_scales_motion_by_elapsed_source_time`. All pass unchanged.
  - Removing the display projection left per-frame tracks and final inventory byte-identical, measured with the real model on the 1080p demo (320 analyses) and the 4K clip (150 analyses).
- **RTI-04 overlays:**
  - The video plays natively. The overlay canvas uses source pixels and the same box and `object-fit` as the video, and redraws only when a result arrives, freshness changes, or overlays are toggled.
  - The video and canvas rectangles matched at 1080p, portrait 4K, the 720p camera, and a 600 by 1,000 viewport, and the boxes sit on their objects in screenshots. This was checked on the development server at commit `a716363`.
  - Dropped frames on the 4K file fell from 512 and 650 per run with the previous canvas redraw to 1 to 5.
  - The start screen is pixel-identical to the previous page. Review and final screens differ only inside the frozen frame.
- **RTI-05 freshness:** with 500 ms added for the first 6 s of a camera run, the page showed "Results delayed". The overlay canvas had 0 painted pixels while delayed, against up to 10,812 while fresh, and the status returned to "Scanning" afterwards.
- **RTI-06 repeatable recorded video:**
  - The 1080p demo analyzed identical timestamps on both runs, each the first frame at or after its grid time, and finalized to the same inventory.
  - 4K 60 fps does not meet this (section F).
  - A file that stops decoding is reported with its stop time, checked by `test_recorded_video_reports_a_file_that_stops_decoding`.
- **tray finalization:** finalize and decision tests pass (36 tests in `test_decision_support.py`, `test_session.py`, and `test_api_sessions.py`). All four recorded browser runs finalized through review to an inventory.

## E. Hugging Face Space profile

Not measured in this round. By the user's decision, deployment evidence was collected on the local workstation GPU only.

## F. limits

- **4K 60 fps repeatability:**
  - Chrome's frame callback skips some displayed frames at 4K 60 fps. One full-file probe found 71 skipped callbacks against 3 dropped frames.
  - A selection whose first frame at or after the grid time was skipped lands one frame, 16.7 ms, late.
  - Two runs then differ in analyzed frames and final inventory. In this round, the scalpel, syringe, and gauze counts differed by one.
  - 1080p 60 fps and 4K 30 fps copies of the same clip were identical across runs.
  - The user accepted this at checkpoint B.2. The RTI-06 wording is open for the architect.
- **Shared workstation:** the browser and server share one workstation, and Chrome ran headless. A physical display or a separate client machine may differ.
- **Fake camera:** the 720p camera is a fake capture device fed from a synthetic video. Its capture time is the page's frame callback clock, so camera latency before the page is not included.
- **Quality path:** tracking quality was measured in process on synthetic sessions, not through the browser.
- **Eval data layout:** this machine stores the eval annotations as one merged file, but the measurement tool expects one file per session. The run used per-session copies generated outside the repository.
- **Load:** only one session was measured. The 8-session limit was not load-tested.
- **Reproducibility:** the browser script is not part of the repository, so the browser measurements cannot be rerun from the repository alone.

## G. commands and results

The suites ran on the CUDA environment's interpreter. `httpx2` and `motmetrics` were supplied on `PYTHONPATH` from a scratch directory, and ruff came from a throwaway virtual environment. The unit and model folders both contain `test_detector.py`, so the suites run separately, as in CI.

```text
ruff check services surgint tests pipelines/measure_realtime.py          all checks passed
python -m pytest -q tests/unit                                           157 passed
python -m pytest -q tests/integration                                    115 passed
python -m pytest -q tests/model                                          10 passed

docker build --target production \
  --build-arg HF_MODEL_ID=AhmedGhita/surgint-instruments-rt-detr \
  --build-arg HF_MODEL_REVISION=bf22ea635858ec05edf272c8c27c36c05bc8f7ce \
  -t surgint-instruments:feat-rt-infer-7e1f306 .
docker run --rm --gpus all -p 127.0.0.1:7862:7860 surgint-instruments:feat-rt-infer-7e1f306

python -m pipelines.measure_realtime models/surgint-instruments-rt-detr --device cuda \
  --data-root <per-session copy of production_v5> --session session_000 \
  --source-fps 10 --duration-seconds 60 --detector-fps 5 --warmup-frames 3
```

The quality command ran once for each session from `session_000` to `session_015`.
