import json
from io import BytesIO
from threading import Event, Lock
from types import SimpleNamespace
from urllib.error import HTTPError
from uuid import uuid4

from PIL import Image

from bridge.ros.surgint_robot_bridge import (
    ActiveRobotRunClient,
    FrameBridge,
    FramePostError,
    HandlingOutcomes,
    SourceTimeSelector,
    annotate_sensor_image,
    encode_sensor_image,
)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def read(self) -> bytes:
        return self._payload


def encoded_image() -> tuple[bytes, str, str]:
    return b"image", "frame.ppm", "image/x-portable-pixmap"


def offer(
    bridge: FrameBridge,
    sequence: int,
    captured_at: float,
    source_image: object = None,
) -> bool:
    return bridge.offer(
        source_sequence=sequence,
        captured_at=captured_at,
        source_width=1920,
        source_height=1080,
        encode_image=encoded_image,
        source_image=source_image,
    )


def robot_response(run_id: str, detections=(), new_results=()) -> dict:
    return {
        "status": {"run_id": run_id},
        "detections": list(detections),
        "new_results": list(new_results),
    }


def tracked(track_id: int, box: tuple[float, float, float, float]) -> dict:
    return {
        "track_id": track_id,
        "class_id": 3,
        "label": "scissors",
        "score": 0.84,
        "box": list(box),
    }


def resolved(item_id: int, outcome: str, action: str | None = None) -> dict:
    return {"item_id": item_id, "handling_outcome": outcome, "action": action}


def test_selector_uses_first_24_fps_image_on_each_source_time_grid_point():
    selector = SourceTimeSelector()

    selected = [index for index in range(25) if selector.select(index / 24.0)]

    assert selected == [0, 5, 10, 15, 20, 24]


def test_bridge_keeps_one_request_in_flight_and_counts_busy_selection():
    started = Event()
    release = Event()
    active = 0
    maximum_active = 0
    posted_sequences = []
    state_lock = Lock()

    def post_frame(**frame) -> str:
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
            posted_sequences.append(frame["source_sequence"])
        started.set()
        assert release.wait(2.0)
        with state_lock:
            active -= 1
        return json.dumps({"new_results": [], "new_inventory_entries": []})

    bridge = FrameBridge(post_frame, lambda _payload: None)
    assert offer(bridge, 0, 0.0)
    assert started.wait(1.0)
    assert not offer(bridge, 1, 0.2)
    release.set()
    assert bridge.wait_until_idle(1.0)
    assert offer(bridge, 2, 0.4)
    assert bridge.wait_until_idle(1.0)

    assert maximum_active == 1
    assert posted_sequences == [0, 2]
    assert bridge.stats.selections == 3
    assert bridge.stats.skipped_busy == 1
    assert bridge.stats.skipped_images == 1
    bridge.close()


def test_bridge_counts_http_429_as_a_skipped_image():
    def reject(**_frame) -> str:
        raise FramePostError(429, "busy")

    bridge = FrameBridge(reject, lambda _payload: None)
    assert offer(bridge, 0, 0.0)
    assert bridge.wait_until_idle(1.0)

    assert bridge.stats.skipped_http_429 == 1
    assert bridge.stats.skipped_images == 1
    assert bridge.stats.post_failures == 0
    bridge.close()


def test_active_client_skips_images_until_a_run_exists(monkeypatch):
    def no_active_run(request, timeout):
        raise HTTPError(request.full_url, 404, "not found", {}, BytesIO(b"{}"))

    monkeypatch.setattr(
        "bridge.ros.surgint_robot_bridge.urlopen",
        no_active_run,
    )
    client = ActiveRobotRunClient("http://127.0.0.1:7860")
    bridge = FrameBridge(client.post_frame, lambda _payload: None)

    assert offer(bridge, 0, 0.0)
    assert bridge.wait_until_idle(1.0)

    assert bridge.stats.skipped_no_active_run == 1
    assert bridge.stats.skipped_images == 1
    assert bridge.stats.post_failures == 0
    bridge.close()


def test_active_client_discovers_a_replacement_after_a_run_ends(monkeypatch):
    first_run_id = uuid4()
    second_run_id = uuid4()
    requested_urls = []
    responses = iter(
        (
            FakeResponse({"status": {"run_id": str(first_run_id)}}),
            HTTPError("frame", 409, "stopped", {}, BytesIO(b"{}")),
            FakeResponse({"status": {"run_id": str(second_run_id)}}),
            FakeResponse({"new_results": [], "new_inventory_entries": []}),
        )
    )

    def urlopen_response(request, timeout):
        requested_urls.append(request.full_url)
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(
        "bridge.ros.surgint_robot_bridge.urlopen",
        urlopen_response,
    )
    client = ActiveRobotRunClient("http://127.0.0.1:7860")
    bridge = FrameBridge(client.post_frame, lambda _payload: None)

    assert offer(bridge, 0, 0.0)
    assert bridge.wait_until_idle(1.0)
    assert offer(bridge, 1, 0.2)
    assert bridge.wait_until_idle(1.0)

    assert requested_urls == [
        "http://127.0.0.1:7860/v1/robot-runs/active",
        f"http://127.0.0.1:7860/v1/robot-runs/{first_run_id}/frames",
        "http://127.0.0.1:7860/v1/robot-runs/active",
        f"http://127.0.0.1:7860/v1/robot-runs/{second_run_id}/frames",
    ]
    assert bridge.stats.skipped_no_active_run == 1
    assert bridge.stats.posted_images == 1
    assert bridge.stats.post_failures == 0
    bridge.close()


def test_successful_responses_are_published_unchanged_in_capture_order():
    responses = []

    def post_frame(**frame) -> str:
        return json.dumps({"source_sequence": frame["source_sequence"]})

    bridge = FrameBridge(post_frame, responses.append)
    assert offer(bridge, 4, 1.0)
    assert bridge.wait_until_idle(1.0)
    assert offer(bridge, 9, 1.2)
    assert bridge.wait_until_idle(1.0)

    assert [json.loads(response)["source_sequence"] for response in responses] == [4, 9]
    assert bridge.stats.posted_images == 2
    assert bridge.stats.published_responses == 2
    bridge.close()


def test_image_encoding_supports_rgb_bgr_and_mono_with_padded_rows(tmp_path):
    messages = [
        SimpleNamespace(
            width=2,
            height=1,
            step=8,
            encoding="rgb8",
            data=bytes((255, 0, 0, 0, 255, 0, 9, 9)),
        ),
        SimpleNamespace(
            width=2,
            height=1,
            step=8,
            encoding="bgr8",
            data=bytes((0, 0, 255, 0, 255, 0, 9, 9)),
        ),
        SimpleNamespace(
            width=2,
            height=1,
            step=4,
            encoding="mono8",
            data=bytes((0, 255, 9, 9)),
        ),
    ]

    decoded = []
    for index, message in enumerate(messages):
        payload, filename, _content_type = encode_sensor_image(message)
        path = tmp_path / f"{index}-{filename}"
        path.write_bytes(payload)
        with Image.open(path) as image:
            decoded.append((image.size, image.convert("RGB").getdata()[0]))

    assert decoded == [
        ((2, 1), (255, 0, 0)),
        ((2, 1), (255, 0, 0)),
        ((2, 1), (0, 0, 0)),
    ]


def test_bridge_annotates_the_posted_image_and_reports_annotation_failures():
    annotated = []
    errors = []
    responses = []

    def post_frame(**frame) -> str:
        return json.dumps({"source_sequence": frame["source_sequence"]})

    def annotate(payload: str, source_image: object) -> None:
        annotated.append((json.loads(payload)["source_sequence"], source_image))
        raise RuntimeError("drawing failed")

    bridge = FrameBridge(post_frame, responses.append, errors.append, annotate)
    assert offer(bridge, 3, 0.0, source_image="camera image")
    assert bridge.wait_until_idle(1.0)

    assert annotated == [(3, "camera image")]
    assert len(responses) == 1
    assert errors == ["annotation failed: drawing failed"]
    assert bridge.stats.published_responses == 1
    assert bridge.stats.post_failures == 0
    bridge.close()


def test_handling_outcome_stays_with_its_item_until_the_run_changes():
    outcomes = HandlingOutcomes()

    outcomes.update(
        robot_response(
            "run-a",
            new_results=[resolved(2, "Recommendation", "transport-to-reprocessing")],
        )
    )
    outcomes.update(robot_response("run-a"))
    assert outcomes.get(2) == ("Recommendation", "transport-to-reprocessing")

    outcomes.update(robot_response("run-b"))
    assert outcomes.get(2) is None


def test_annotation_colors_boxes_by_handling_outcome_for_each_encoding():
    width, height = 200, 120
    response = robot_response(
        "run-a",
        detections=[
            tracked(1, (20, 60, 90, 110)),
            tracked(2, (110, 60, 180, 110)),
            tracked(3, (150, 5, 195, 30)),
        ],
        new_results=[
            resolved(1, "Recommendation", "transport-to-reprocessing"),
            resolved(2, "Needs review"),
        ],
    )
    outcomes = HandlingOutcomes()
    outcomes.update(response)

    def message(encoding: str, channels: int, marker: bytes) -> SimpleNamespace:
        step = width * channels + 4
        data = bytearray(step * height)
        offset = 5 * step + 5 * channels
        data[offset : offset + channels] = marker
        return SimpleNamespace(
            width=width,
            height=height,
            step=step,
            encoding=encoding,
            data=bytes(data),
        )

    cases = [
        (message("rgb8", 3, bytes((255, 0, 0))), (255, 0, 0)),
        (message("bgr8", 3, bytes((0, 0, 255))), (255, 0, 0)),
        (message("mono8", 1, bytes((200,))), (200, 200, 200)),
    ]
    for source, marker in cases:
        pixels = annotate_sensor_image(source, response, outcomes)
        image = Image.frombytes("RGB", (width, height), pixels)

        assert image.getpixel((5, 5)) == marker
        assert image.getpixel((55, 110)) == (89, 215, 176)
        assert image.getpixel((145, 110)) == (255, 198, 109)
        assert image.getpixel((150, 30)) == (127, 199, 255)
        assert image.getpixel((55, 85)) == (0, 0, 0)
