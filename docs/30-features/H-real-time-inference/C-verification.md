# verification

> records the measurement-gate evidence for the existing sequential real-time inference path.

**status:** measurement gate, awaiting profile approval

## A. evidence scope

This checkpoint instruments the current sequential path without changing its scheduling,
tracking, inventory, or finalization behavior. The recorded run is a development diagnostic,
not deployment acceptance and not evidence that the product supports a live detector rate.

The raw report is `baseline-development-cpu.json`. It was produced on:

- Windows 11, 13th Gen Intel Core i7-1360P, 16 logical CPUs;
- Python 3.12.7 and CPU-only PyTorch 2.4.1;
- `models/fair-raven`, manifest schema 1, 1024 by 576 model input;
- annotated synthetic `session_000`, 1280 by 720 source frames;
- an assumed 20 FPS source and display profile, using the first 5 seconds;
- JPEG quality 90, class-agnostic NMS at 0.7, one stream, and sequential requests.

The laptop is temporary development hardware. Every supported-profile numerical limit must be
rerun and approved on the actual robot-edge or tray-service deployment hardware.

## B. instrumentation evidence

- `Pipeline.last_timing` records monotonic preprocessing, inference, postprocessing, tracking,
  and total durations without changing the returned detections.
- The frame endpoint returns `Server-Timing` entries for request receipt and multipart parsing,
  image decode, lock wait, pipeline phases, inventory update, and total server time.
- The browser keeps at most 1,000 in-memory samples for capture encoding, request and response,
  first and held display age, busy source frames, admitted frames, and overwrites. It sends no
  image content or timing telemetry elsewhere.
- The development measurement command drives the real checkpoint through the frame API, then
  replays measured service times against the existing no-pending-work behavior. It evaluates
  tracking and inventory on the nominal 5, 6, and 10 FPS selections processed offline in order.

## C. latency breakdown

Values are milliseconds and shown as p50 / p95. `response boundary` is TestClient time outside
the measured server total, so it is not a network measurement. `capture to result` begins before
JPEG encoding and ends after response receipt and JSON parsing.

| phase | 5 FPS | 6 FPS | 10 FPS |
|---|---:|---:|---:|
| capture JPEG encode | 5.4 / 9.1 | 5.8 / 12.9 | 5.7 / 8.5 |
| receive and multipart parse | 1.4 / 2.2 | 1.4 / 2.8 | 1.3 / 2.3 |
| image decode | 8.4 / 12.2 | 9.3 / 13.3 | 8.5 / 14.8 |
| session and inference lock wait | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| preprocess | 23.7 / 28.0 | 23.4 / 34.3 | 22.7 / 34.2 |
| detector inference | 1,106.7 / 1,168.7 | 1,112.3 / 1,319.6 | 1,116.9 / 1,209.7 |
| postprocess and NMS | 3.9 / 5.7 | 4.0 / 5.4 | 3.6 / 6.6 |
| tracking | 9.2 / 12.9 | 8.6 / 17.3 | 9.4 / 17.1 |
| inventory update | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.2 |
| total server | 1,158.3 / 1,233.0 | 1,162.0 / 1,384.6 | 1,168.7 / 1,267.9 |
| response boundary | 2.3 / 2.8 | 2.1 / 4.5 | 2.0 / 3.3 |
| capture to result | 1,169.1 / 1,244.1 | 1,170.3 / 1,398.7 | 1,175.9 / 1,279.1 |

Inference accounts for about 95 percent of median server time. JPEG capture, decode,
postprocessing, tracking, inventory, and the in-process response boundary are not the bottleneck
on this profile. No model optimization is approved by this result.

## D. detector-rate and overlay behavior

The current camera path waits for each response and has no independent display clock. Its
first-display overlay-age proxy is therefore the measured capture-to-result latency above, while
the visible frame itself also advances only when a result completes.

The recorded-video path advances display independently, holds the last returned boxes, and has
no pending-frame slot. Replaying measured service times over five seconds produced:

| requested rate | p95 service / interval | admitted / candidates | effective rate | busy source frames | overwritten | held-overlay age p50 / p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 5 FPS | 6.22 | 4 / 25 | 0.8 FPS | 21 | 0 | 1,850 / 2,500 ms |
| 6 FPS | 8.39 | 4 / 30 | 0.8 FPS | 26 | 0 | 1,808 / 2,425 ms |
| 10 FPS | 12.79 | 5 / 50 | 1.0 FPS | 45 | 0 | 1,800 / 2,350 ms |

None of the requested rates is sustainable on this laptop. The current implementation does not
overwrite frames because it has no pending slot. A source frame that passes while recorded-video
inference is busy is never admitted, while the camera loop cannot enumerate source frames that
pass during its blocking wait. Actual browser-displayed overlay age was not measured in this
headless run. The browser instrumentation is present for a later supervised run.

## E. tracking, confirmation, and inventory effects

These quality values use the same first five seconds at each nominal selection rate, processed
offline in source order so every selected frame is retained. They do not describe the much lower
effective rates produced by the overloaded scheduler simulation.

| selected rate | MOTA | IDF1 | identity switches | first confirmation source delay | sequential wall delay | predicted / 39 inventory items | absolute inventory error |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 FPS | 0.422 | 0.596 | 2 | 800 ms | 6,010 ms | 24 | 15 |
| 6 FPS | 0.454 | 0.627 | 0 | 700 ms | 5,836 ms | 25 | 14 |
| 10 FPS | 0.481 | 0.649 | 4 | 400 ms | 5,776 ms | 27 | 12 |

All three profiles first emit confirmed tracks on selected sample five, matching
`CONFIRM_HITS = 5`. A higher nominal selection rate reduces source-time confirmation delay and
improves this short-window inventory undercount, but 10 FPS still misses 12 of 39 items and has
four identity switches. The five-second window, synthetic camera orbit, and fixed-step tracker
are insufficient for an acceptance-quality comparison.

Inventory receives only confirmed detector-backed outputs in the current implementation. There
are no display-only predictions yet, so the measured display path cannot add tracking evidence,
inventory entries, or handling decisions. Existing one-shot finalization tests remain the
regression evidence for decision behavior at this gate.

## F. provisional engineering guardrails

These are implementation guardrails for the next measured iteration, not supported product
limits:

- begin target-hardware evaluation at 5 detector FPS;
- require p95 capture-to-result service time at or below 80 percent of the selected interval,
  which is 160 ms at 5 FPS, 133 ms at 6 FPS, and 80 ms at 10 FPS;
- treat one detector interval as normal overlay age and suppress an overlay after two intervals,
  initially 400 ms at 5 FPS;
- expose degraded operation whenever the selected rate is not sustained or an overwrite occurs;
- retain exactly one processing frame and at most one newest pending live frame;
- keep five-hit confirmation only provisionally, with a 1,000 ms confirmation guardrail at
  5 FPS, and convert confirmation and loss behavior to elapsed-time semantics before approval;
- set no tracking, identity-switch, prediction-error, or inventory acceptance threshold from
  this diagnostic. Those require representative motion and complete sequences on target hardware.

## G. smallest sufficient implementation proposal

Subject to architect and user approval at this gate, continue the existing `B-plan.md` without a
new transport or infrastructure:

1. add source identity, frame sequence, monotonic capture time, and result timing metadata;
2. make Kalman prediction, confirmation, and expiration use elapsed source time;
3. keep detector-backed confirmed observations separate from non-mutating display predictions;
4. add one processing frame plus one overwriteable newest pending frame for live input;
5. suppress display predictions beyond the approved age or validity condition and expose degraded
   state;
6. keep recorded input deterministic, in order, and aligned to the exact source frame;
7. preserve current inventory, one-shot tray finalization, and decision behavior;
8. rerun 5, 6, and 10 FPS on target hardware before selecting the supported profile or considering
   WebSockets, Triton, model conversion, additional workers, or infrastructure.

## H. verification commands and results

Development measurement:

```text
python -m pipelines.measure_realtime models/fair-raven --duration-seconds 5 --detector-fps 5 6 10 --warmup-frames 2 --output docs/30-features/H-real-time-inference/baseline-development-cpu.json
```

Focused checks:

```text
python -m ruff check services/api/app.py surgint/runtime/pipeline.py pipelines/measure_realtime.py tests/unit/test_pipeline.py tests/unit/test_console_ui.py tests/unit/test_realtime_measurement.py tests/integration/test_api_sessions.py
python -m pytest -q tests/unit/test_realtime_measurement.py tests/unit/test_pipeline.py tests/unit/test_console_ui.py tests/integration/test_api_sessions.py
```

Result: Ruff passed and 36 focused tests passed. Pytest emitted two cache-write warnings because
the existing `.pytest_cache` directory was not writable; test execution and results were not
affected.

The verification script itself was blocked by the host PowerShell execution policy. Its exact
equivalent checks were run with pytest cache disabled and a workspace `--basetemp` to avoid the
host temp-directory ACL failure:

```text
python -m ruff check services surgint tests
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/unit tests/unit
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/integration tests/integration
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/model tests/model
```

Result: Ruff passed, 127 unit tests passed, 110 integration tests passed, and 10 model tests
passed. The workspace verification temp directory was removed after the checks.

## I. limitations and gate decision

- no target GPU, robot-edge device, cloud GPU, real browser, camera, network, concurrent stream,
  or deployment container was exercised;
- source FPS is an explicit playback assumption because the annotated image sequence carries no
  timing metadata;
- the in-process client excludes real network latency and browser JPEG implementation cost;
- held-overlay age is simulated from measured service times, and prediction error is not available
  because display prediction is not implemented;
- quality evidence covers one synthetic sequence and only its first five seconds;
- fixed-step tracking means rate comparisons also change the tracker's implicit time unit;
- no supported detector rate or acceptance threshold is approved at this gate.

Stop here for architect and user approval. Do not optimize or continue to temporal contracts,
scheduling, prediction, or recorded-video changes before that decision.
