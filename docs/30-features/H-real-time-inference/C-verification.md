# verification

> records the measurement-gate and temporal-contract evidence for real-time inference.

**status:** temporal and tracking contract checkpoint, awaiting commit

## A. evidence scope

The measurement checkpoint instruments the current sequential path without changing its scheduling,
tracking, inventory, or finalization behavior. The recorded run is a development diagnostic,
not deployment acceptance and not evidence that the product supports a live detector rate.

The development CPU raw report is `baseline-development-cpu.json`. It was produced on:

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
- The same command now has a remote mode that paces source candidates against the wall clock,
  calls the public frame API, records the server phases and client boundary, and evaluates only
  frames that were actually admitted. It does not change the server or browser scheduler.

## C. latency breakdown

Values are milliseconds and shown as p50 / p95. `response boundary` is TestClient time outside
the measured server total, so it is not a network measurement. `capture to result` begins before
JPEG encoding and ends after the response body is received; JSON parsing follows that interval.

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

Remote measurement support and report checks after the T4 run:

```text
python -m ruff check pipelines/measure_realtime.py tests/unit/test_realtime_measurement.py
python -m pytest -q -p no:cacheprovider tests/unit/test_realtime_measurement.py
python -m pipelines.measure_realtime --help
python -c "import json, pathlib; p=pathlib.Path(r'docs/30-features/H-real-time-inference/baseline-space-t4-small.json'); d=json.loads(p.read_text(encoding='utf-8')); assert [r['requested_detector_fps'] for r in d['rates']] == [5.0, 6.0, 10.0]; assert d['space_lifecycle']['paused_after_measurement'] is True; assert d['space_lifecycle']['cleanup_errors'] == []; print('GPU report schema and lifecycle assertions passed')"
```

Result: focused Ruff passed, all 4 measurement tests passed, the CLI help completed, and the raw
report schema and lifecycle assertions passed.

Change-verification equivalents were rerun after the remote support was added:

```text
python -m ruff check services surgint tests pipelines/measure_realtime.py
New-Item -ItemType Directory -Path '.verification_tmp' -Force
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/gpu-unit-rerun tests/unit
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/gpu-integration-rerun tests/integration
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/gpu-model tests/model
```

Result: Ruff passed, 128 unit tests passed, 110 integration tests passed, and 10 model tests
passed. An initial parallel unit and integration attempt could not create nested base-temp paths
because the common parent did not yet exist. After explicitly creating that parent, both suites
passed unchanged. The resolved workspace temp directory was removed after verification.

## I. bounded T4 remote evidence

The second raw report is `baseline-space-t4-small.json`. This is an actual remote measurement of
the instrumented API, but it is still a development diagnostic and not deployment acceptance.
The temporary Space deployment used:

- public Docker Space `AhmedGhita/surgint-instruments`, revision
  `d5af3110d58c258170891792c01b75adbab3f6ba`, on requested and running hardware `t4-small`;
- source commit `936ed3c4cb956c78d04cbe4b1e52652822c431d9` from branch `feat/rt-infer`, installed from a
  pinned source archive with SHA-256
  `cc4ae1cd020089d86896062fb48fd320d452c0891dee728ea3f898a08bcb13ca`;
- base image `ghcr.io/ahmedghita1/surgint-instruments:1.0.1` pinned to manifest digest
  `sha256:cec843003b132fcd4ea791086e14e2032b2b1da8cb9c63ced37baba11ab17b1d`;
- model source `PekingU/rtdetr_r18vd_coco_o365`, training run
  `fair-raven_20260917_1701`, dataset `production_v5`, input 1024 by 576, and weights SHA-256
  `sha256:ef6c387cfac708da21bd51261f0d35d94f37237eb5e8aa3731f2c6b010a27dd0`.

The model repository revision was not present in the image manifest and is recorded as unknown,
not inferred. The source profile was the first five seconds of annotated synthetic `session_000`,
assuming 20 FPS source and display clocks, using 1280 by 720 JPEG frames at quality 90, one stream,
two warmup requests, and sequential public HTTPS request-response calls. Candidate source times were
paced on the client wall clock. A candidate whose slot passed while a request was in flight was
counted busy and not admitted. Tracking and inventory were evaluated only on admitted frames.

## J. T4 latency breakdown

Values are milliseconds and shown as p50 / p95. `response boundary` is request time outside the
route's `Server-Timing` total. It includes the public HTTPS path, Space proxying, framework work
outside the timed route, response serialization, and body transfer, so it is not a pure network
measurement. `capture to result` includes local JPEG encoding through response body receipt.

| phase | 5 FPS | 6 FPS | 10 FPS |
|---|---:|---:|---:|
| client JPEG encode | 6.5 / 9.7 | 6.6 / 8.4 | 6.5 / 7.5 |
| receive and multipart parse | 22.0 / 25.5 | 22.3 / 31.3 | 22.3 / 23.9 |
| image decode | 5.9 / 7.5 | 6.1 / 6.2 | 6.1 / 7.6 |
| session and inference lock wait | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| preprocess | 16.1 / 19.7 | 15.6 / 18.2 | 15.5 / 25.4 |
| detector inference | 26.4 / 28.5 | 26.7 / 29.1 | 26.9 / 38.3 |
| postprocess and NMS | 2.5 / 2.9 | 2.5 / 3.2 | 2.4 / 3.4 |
| tracking | 2.9 / 4.1 | 3.5 / 3.9 | 3.5 / 5.6 |
| inventory update | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| total server | 78.2 / 83.1 | 78.7 / 87.5 | 77.4 / 103.5 |
| response boundary | 169.4 / 194.4 | 156.2 / 180.2 | 152.0 / 160.1 |
| capture to result | 254.2 / 283.6 | 244.3 / 279.1 | 236.6 / 263.2 |

GPU inference was not the end-to-end bottleneck in this topology. Median inference was about
26 to 27 ms and median total server time was about 77 to 79 ms. The public client boundary was
larger than server time. This does not authorize transport or model changes.

## K. T4 detector-rate and overlay behavior

The admissions and latency values below were measured during actual wall-clock-paced requests.
Held-overlay age was replayed afterward on the assumed 20 FPS display clock from the actual capture
and result timestamps. It is not a browser rendering measurement.

| requested rate | p95 service / interval | admitted / candidates | effective rate | completion rate | busy | overwritten | first-display proxy p50 / p95 | held age p50 / p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 FPS | 1.42 | 13 / 25 | 2.6 FPS | 2.47 FPS | 12 | 0 | 254 / 284 ms | 448 / 646 ms |
| 6 FPS | 1.67 | 14 / 30 | 2.8 FPS | 2.72 FPS | 16 | 0 | 244 / 279 ms | 434 / 614 ms |
| 10 FPS | 2.63 | 16 / 50 | 3.2 FPS | 3.06 FPS | 34 | 0 | 237 / 263 ms | 388 / 551 ms |

None of 5, 6, or 10 detector FPS was sustained by the current synchronous public path. The
implementation overwrote zero frames because it has no pending-frame slot; 12, 16, and 34 source
candidates instead passed while work was busy. The lower held age at a higher requested rate is a
sampling effect from admitting a more recent eligible candidate, not evidence of sustained 10 FPS.

## L. T4 tracking, confirmation, and inventory effects

These values describe the irregular frames actually admitted during each five-second run.

| requested rate | MOTA | IDF1 | identity switches | first confirmation source / wall delay | predicted / 39 inventory items | absolute inventory error |
|---:|---:|---:|---:|---:|---:|---:|
| 5 FPS | 0.322 | 0.492 | 0 | 1,600 / 1,952 ms | 23 | 16 |
| 6 FPS | 0.359 | 0.536 | 0 | 1,350 / 1,635 ms | 24 | 15 |
| 10 FPS | 0.337 | 0.510 | 1 | 1,300 / 1,595 ms | 21 | 18 |

Every run first confirmed on admitted sample five, preserving the existing five-hit rule. Busy
slots extended source-time and wall-time confirmation, and the short runs undercounted inventory
by 15 to 18 items. The 10 FPS request did not improve tracking or inventory because it did not
produce a sustained 10 FPS observation stream. Existing tracking is fixed-step, so these values
support the need for elapsed-time semantics but are not quality acceptance thresholds. Display-only
predictions do not exist at this gate and therefore cannot update tracking evidence, inventory, or
handling decisions.

## M. numerical recommendation and smallest sufficient proposal

Keep the guardrails in section F as provisional engineering targets. In particular, begin the next
target-hardware evaluation at 5 FPS, require p95 capture-to-result at or below 160 ms, suppress a
5 FPS overlay after 400 ms, retain at most one newest pending live frame, and require confirmation
within 1,000 ms. This Space profile failed the 5 FPS service, held-overlay, and confirmation targets.

Do not declare a supported detector rate from this result. Supported-profile numerical limits must
be rerun on the actual target deployment hardware and network topology. The smallest sufficient
implementation remains section G and `B-plan.md`: temporal identity, elapsed-time tracking,
non-mutating display predictions, a bounded latest-frame live scheduler, stale-result suppression,
deterministic recorded input, and unchanged tray finalization and decision behavior.

## N. Space restoration and pause evidence

- initial Space revision `e7201f56971fb21f57899eca8713a9c8ac5529f4` was `PAUSED`, with requested
  hardware `t4-small` and sleep time 900 seconds;
- measurement ran from `2026-10-11T13:06:54.126125+00:00` through
  `2026-10-11T13:07:14.614018+00:00`;
- cleanup restored revision `13f6f6e6c0b5d1433f867bca140d393e679a14b2` and returned the Space to
  `PAUSED` with no cleanup errors;
- the restored 50-byte Dockerfile has SHA-256
  `43be37c03e4b9168b24cfa8a0aa621baae3a5e7585e7a56e44cb1dc6c91a404c` and exactly contains
  `FROM ghcr.io/ahmedghita1/surgint-instruments:1.0.1`;
- the preserved 226-byte README has SHA-256
  `30a0a12092088fa02693e24769094d4945f94874750e31f41dbcc90d4c697310`.

An independent read after the cleanup confirmed revision
`13f6f6e6c0b5d1433f867bca140d393e679a14b2`, stage `PAUSED`, no allocated current hardware,
requested hardware `t4-small`, sleep time 900, and the same Dockerfile and README hashes.

## O. combined limitations and gate decision

- neither the temporary CPU laptop nor the public T4 Space is the confirmed deployment target;
- the remote evidence is one bounded run per rate, one synthetic sequence, one stream, and only
  five seconds per rate, so it does not estimate long-run tails, contention, or thermal behavior;
- source FPS is an explicit playback assumption because the annotated image sequence carries no
  timing metadata;
- the remote client exercised a real public network path, but did not isolate network RTT, proxy
  overhead, browser JPEG behavior, rendering, a physical camera, or concurrent streams;
- held-overlay age is replayed from actual timestamps, not observed in a browser, and prediction
  error is unavailable because display prediction was not implemented in the measured build;
- the measured build used fixed-step tracking, so rate comparisons also changed the tracker's
  implicit time unit;
- the base image and weights are content-addressed, but the upstream model repository revision was
  unavailable from the image manifest;
- no supported detector rate or acceptance threshold is approved at this gate.

The architect and user approved proceeding from this measured profile to the temporal and tracking
contract checkpoint. Optimization and supported-profile selection remain unapproved. Scheduler,
overlay-rendering, and recorded-video changes remain deferred to later checkpoints.

## P. temporal frame and result contract

The frame route now supports two explicit compatibility modes:

- the supported client path supplies schema version 1.1, source identity, sequence, monotonic
  capture timestamp, source width, and source height as one all-or-none form set;
- the compatibility path supplies none of those fields and receives an internal sequential source
  identity and deterministic timestamp advanced by the tracker's nominal 0.2-second interval,
  marked `server-generated-legacy`. This synthetic timing preserves fifth-observation confirmation
  for existing clients; it is not measured source timing and not acceptance evidence.

Partial metadata and invalid field values are rejected. A client-bound session rejects source
changes, repeated or decreasing sequence values, repeated or decreasing capture timestamps, and
declared dimensions that differ from the decoded image. Source/order state remains isolated per
session. Identity state is recorded only after the detector-backed result updates the inventory.

Frame responses retain the existing `frame_count` and `detections` fields and add schema version
1.1, the accepted frame identity including metadata origin, and monotonic server receipt,
processing-start, processing-complete, and result-creation boundaries. The packaged console and
the local and remote measurement harnesses send the complete client metadata set. No transport or
scheduler behavior changed in this checkpoint.

## Q. elapsed-time tracking contract

Kalman prediction now scales constant-velocity motion and process noise by elapsed source time.
For the same timestamped detection sequence, repeated runs produce the same track identities,
boxes, filter state, and observation history.

Track confirmation requires both five detector-backed observations and at least 0.8 seconds from
the first through the latest matched observation. Thus a 5 FPS stream can confirm on its fifth
observation at 0.8 seconds, while five observations at 10 FPS remain tentative and confirmation
occurs on the ninth observation at 0.8 seconds. The legacy direct-runtime bridge advances by the
0.2-second reference interval, preserving the prior five-update confirmation point for callers
that do not yet provide timestamps.

Loss is elapsed-time based. Unless explicitly overridden, its timeout is `track_buffer` multiplied
by the fixed 0.2-second reference interval, not by the number or rate of subsequent tracker calls.
Invalid and non-advancing explicit tracker timestamps are rejected before the update proceeds.

## R. display prediction isolation

The runtime and a read-only API route expose display-only projections for tracks that have been
confirmed at least once. Each projection includes track identity, class and score, projected box,
track state, last detector-backed state timestamp, prediction age, positional uncertainty, and a
validity value of `valid`, `too-old`, `non-finite`, or `invalid-geometry`. The provisional runtime
age condition is 0.4 seconds, carried forward from the measurement guardrail; actual suppression
in the console is a later checkpoint.

Focused tests snapshot the filter mean and covariance, hit count, class votes and scores,
observation timestamps, track lifecycle state and timestamps, and tracker timestamp before a
display projection. Repeated projections return the same result and leave every snapshot value
unchanged. The projected box is read-only. Integration tests compare otherwise identical sessions
with and without display-prediction reads and prove unchanged inventory frame counts and identical
finalized item decisions. Display-only predictions therefore add no hits, votes, observations, or
history and do not update inventory, session frame counts, finalization, or handling decisions.

Confirmed detector-backed frame responses retain their existing meaning. The display endpoint
does not write to the detector-backed response, and display reads remain available after
finalization without reopening or changing the finalized session.

## S. temporal checkpoint verification

Focused checks:

```text
python -m ruff check surgint/runtime/temporal.py surgint/runtime/kalman.py surgint/runtime/bytetrack.py surgint/runtime/pipeline.py services/api/sessions.py services/api/schemas.py services/api/app.py pipelines/measure_realtime.py tests/unit/test_temporal.py tests/unit/test_kalman.py tests/unit/test_bytetrack.py tests/unit/test_pipeline.py tests/unit/test_console_ui.py tests/unit/test_realtime_measurement.py tests/integration/test_api_sessions.py tests/integration/test_session.py tests/integration/test_decision_support.py
python -m pytest -q -p no:cacheprovider tests/unit/test_temporal.py tests/unit/test_kalman.py tests/unit/test_bytetrack.py tests/unit/test_pipeline.py tests/unit/test_console_ui.py tests/unit/test_realtime_measurement.py tests/integration/test_api_sessions.py tests/integration/test_session.py tests/integration/test_decision_support.py
```

Result: focused Ruff passed and all 95 focused tests passed.

The repository verification script remains blocked by the host PowerShell execution policy
recorded in section H. Its equivalent commands ran with a workspace base-temp directory:

```text
New-Item -ItemType Directory -Path '.verification_tmp' -Force
python -m ruff check services surgint tests pipelines/measure_realtime.py
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/temporal-unit tests/unit
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/temporal-integration tests/integration
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/temporal-model tests/model
```

Result: Ruff passed, 148 unit tests passed, 114 integration tests passed, and 10 model tests passed.
The model suite completed in 401.82 seconds.

An optional `ruff format --check` diagnostic was not part of the repository verification script.
It reported existing format drift in eight mixed pre-existing and changed files, including
long-standing test formatting. No bulk formatting rewrite was made in this scoped checkpoint;
the required Ruff lint check passed.

The remaining limitations are explicit:

- legacy-generated timestamps are compatibility-only and cannot support source-time acceptance;
- the console sends full temporal metadata but still uses the existing sequential request loop and
  does not consume display predictions;
- the 0.4-second display validity guardrail is provisional, and no UI stale-overlay suppression is
  implemented yet;
- recorded-video processing still uses the deterministic legacy 0.2-second runtime bridge rather
  than an exact persisted source timestamp contract;
- the bounded latest-frame scheduler, overwrite slot, independent browser display clock, and
  target-hardware 5, 6, and 10 FPS rerun remain future checkpoints;
- this checkpoint changes no tray inventory evidence rule, finalization rule, handling decision,
  transport, serving infrastructure, model, or worker topology.

## T. legacy API compatibility correction

Architecture review found that using request-arrival time for omitted-metadata API frames could
prevent a fast legacy client from accumulating the 0.8 elapsed seconds now required for
confirmation. The compatibility bridge therefore starts each legacy session at synthetic source
time 0.0 and advances by the tracking pipeline's nominal interval, currently 0.2 seconds. This
preserves the historical fifth-observation confirmation point deterministically while retaining
the `server-generated-legacy` origin and non-acceptance status. Client-supplied timestamps remain
strictly increasing source time and are not replaced or relaxed by this bridge.

An API integration regression submits five matching frames without temporal form fields. It
verifies synthetic timestamps 0.0 through 0.8, no confirmed response on frames one through four,
track confirmation on frame five, and a finalized inventory containing the detected class with
count one.

Correction verification:

```text
python -m ruff check services/api/app.py services/api/sessions.py tests/integration/test_api_sessions.py
python -m pytest -q -p no:cacheprovider tests/integration/test_api_sessions.py tests/unit/test_temporal.py tests/unit/test_bytetrack.py tests/unit/test_pipeline.py tests/integration/test_session.py tests/integration/test_decision_support.py
New-Item -ItemType Directory -Path '.verification_tmp' -Force
python -m ruff check services surgint tests pipelines/measure_realtime.py
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/legacy-unit tests/unit
python -m pytest -q -p no:cacheprovider --basetemp .verification_tmp/legacy-integration tests/integration
```

Result: focused Ruff passed, 70 targeted tests passed, repository Ruff passed, 148 unit tests
passed, and 115 integration tests passed. The previously completed 10-test model suite was not
repeated because this correction changes only API compatibility time synthesis and its integration
test, not detector or model behavior.
