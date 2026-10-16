# verification

> records the current evidence for the robot workflow package.

**status:** verification failed

## A. acceptance profile

Measured on 2026-10-16 with one active robot run and no concurrent tray session.

- workstation: NVIDIA GeForce RTX 4090 (24,564 MiB), driver 560.35.05; AMD Ryzen Threadripper PRO 7955WX (16 cores, 32 threads); Ubuntu 22.04.5, kernel 6.8.0-136;
- runtime: ROS 2 Humble with `rmw_fastrtps_cpp`; local CUDA API on port 7861; Chrome 151.0.7922.71 in headless mode with Vulkan ANGLE, Vulkan enabled, and the GPU blocklist ignored;
- ROS contract used for the measurement: `/camera/image_raw` as `sensor_msgs/msg/Image`; `/surgint/robot_results` as `std_msgs/msg/String` containing the unchanged frame API response JSON;
- model: RT-DETR R18VD from `PekingU/rtdetr_r18vd_coco_o365`, trained as `fair-raven_20260917_1701` on dataset `production_v5`, input 1024 by 576, weights `sha256:ef6c387cfac708da21bd51261f0d35d94f37237eb5e8aa3731f2c6b010a27dd0`, NMS IoU 0.7;
- input: `data/synthetic/demos/demo.mp4`, 1,920 by 1,080, 1,536 frames, 64.0 seconds at 24 fps;
- replay: all 1,536 frames offered as ROS images at an observed 24.027599 fps over 63.884867 seconds, using image-header source time and the 0.2-second selection rule;
- overload behavior: the bridge permits one in-flight request and has no pending-frame queue. Due images are skipped while that request is active or after HTTP 429.

Robot edge hardware was not measured and no robot-edge performance claim is made.

## B. required evidence

- `python -m ruff check bridge services surgint tests`: passed.
- `python -m pytest -q tests/unit`: 174 passed in 2.61 seconds. This includes lifecycle, exactly-once item resolution, deterministic ordering, immutable result fields, decisions, failure states, bridge selection, single-request behavior, counted skips, response order, and image encoding.
- `python -m pytest -q tests/integration` with the three TestClient modules excluded: 92 passed in 2.54 seconds. This includes tracking, inventory, decision support, and tray-domain regressions.
- `python -m pytest -q tests/model`, run in the CUDA environment with `motmetrics` supplied from the disposable test environment: 10 passed in 8.33 seconds.
- Live robot API checks on the GPU covered readiness, active-run conflict, temporal frame metadata, inference, state, stop, rejected post-stop input, immutable summary, export, release, and isolated restart.
- The robot-operator browser walkthrough covered start, live result and inventory rendering, a `Needs review` result, degraded timing, stop, summary, export, release, failure presentation, and visible research-only safety language.
- ROS replay verified selection from image-header time, at most one request in flight, counted skips, unchanged response JSON publication, and result ordering.
- A live tray-session GPU smoke test created a session, accepted six legacy frame requests, finalized one syringe inventory item, and rejected post-finalization input with HTTP 409.

The TestClient modules `test_api_health.py`, `test_api_robot_runs.py`, and `test_api_sessions.py` could not run on this workstation: the CUDA environment lacks their test dependencies, and a direct health-module attempt in the disposable test environment did not complete within 20 seconds. Their domain behavior is covered by the passing unit and non-TestClient integration suites, and the main API paths were exercised against the live CUDA service.

## C. recorded results

| Metric | Observed | Target | Result |
| --- | ---: | ---: | --- |
| Analyses per second | 4.90625 (314 analyses / 64.0 seconds) | at least 5 | **fail** |
| Item-to-page-visibility latency, p95 | 293.7669 ms across 16 resolved items | at most 300 ms | pass |
| Queued images | 0 | 0 | pass |

The browser latency was measured from publication of the ROS image that resolved an item until the browser fetch handler had rendered that result and its inventory entry. The measured p50 was 171.8446 ms and the maximum was 302.6871 ms. As a supplementary bridge measurement, result-topic publication latency had a p50 of 60.7441 ms, p95 of 65.6122 ms, and maximum of 67.2070 ms across the same 16 items.

The bridge received 1,179 of the 1,536 best-effort ROS image messages, selected 316, posted and published 314 responses, skipped 2 while busy, received no HTTP 429 response, and recorded no post failure. The bridge has no queue and its measured maximum active request count was one, so the two busy selections were dropped rather than queued.

**ROB-07 result: fail.** Throughput was 0.09375 analyses per second below the required minimum. The latency and no-queue targets passed, but package acceptance cannot be demonstrated because every ROB-07 target is required.

## D. limitations

- The ROS version, image topic, image message type, result destination, and result message type remain TBD in `A-spec.md`. The measured ROS contract is the user's temporary assumption pending confirmation from the robot integration colleague.
- Best-effort ROS sensor QoS delivered 1,179 of 1,536 locally published images during the native-rate replay. This did not create a bridge queue, but it reduced the images available to the selector.
- The full TestClient regression modules remain unavailable as described above.
- The package builds on the current H real-time contracts at the user's direction. The outstanding findings in `H-real-time-inference/D-review.md` remain outside this checkpoint.
- No robot edge hardware, robot actuation, public-network operation, durable storage, multi-worker behavior, or Hugging Face Space deployment was evaluated.
