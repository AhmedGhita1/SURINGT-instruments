# implementation plan

> defines the measured implementation path from the current sequential video path to the shared real-time runtime.

**status:** proposed

## A. foundation

the repository already provides one shared detector, ordered frame inference, ByteTrack, session inventory, request-response frame processing, browser camera capture, and recorded-video playback. The current camera loop waits for inference, the recorded-video overlay can use a result from an older frame, and tracking advances one fixed step per detector update.

## B. approach

1. instrument capture, admission, server receipt, inference, tracking, response, and display without changing scheduling behavior.
2. add source identity, sequence, capture time, and timing metadata to the frame and result contracts.
3. make Kalman and track lifecycle updates use elapsed source time and provide a non-mutating display prediction contract.
4. separate confirmed detector-backed track output from display-only predicted track output.
5. implement a live scheduler with configurable selection rate, one processing frame, and one newest-frame overwrite slot.
6. render current-time predictions independently of detector completion and suppress stale or invalid overlays.
7. implement deterministic recorded-video processing with exact frame-to-result alignment.
8. evaluate 5, 6, and 10 FPS selection rates, select numerical limits, and optimize only the measured bottleneck.
9. run tray regressions and expose workflow-neutral contracts for the robot coordinator.

## C. measurement gate

after the instrumented baseline, the implementation lead shall return the latency breakdown, sustainable detector rate, overlay age, tracking effects, and recommended numerical limits. The architect and user approve the supported profile before optimization or a material serving change continues.

## D. affected boundaries

- `surgint/runtime`: variable-time Kalman prediction, tracking timestamps, and separate observation and display outputs;
- `services/api`: temporal request and response metadata, bounded live scheduling, timing status, and recorded-video alignment;
- `services/api/static/index.html`: independent rendering, current-time prediction, stale-overlay suppression, and degraded presentation;
- evaluation and tests: temporal metrics, variable-rate sequences, synchronization, tracking, inventory, and workflow regressions.

## E. escalation conditions

return a change proposal before introducing a new transport, inference server, model conversion, additional worker, camera-motion model, or changed inventory evidence rule. Include the measured bottleneck, expected benefit, cost, and smallest viable alternative.
