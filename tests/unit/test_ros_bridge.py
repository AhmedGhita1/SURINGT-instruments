import json
from threading import Event, Lock
from types import SimpleNamespace

from PIL import Image

from bridge.ros.surgint_robot_bridge import (
    FrameBridge,
    FramePostError,
    SourceTimeSelector,
    encode_sensor_image,
)


def encoded_image() -> tuple[bytes, str, str]:
    return b"image", "frame.ppm", "image/x-portable-pixmap"


def offer(bridge: FrameBridge, sequence: int, captured_at: float) -> bool:
    return bridge.offer(
        source_sequence=sequence,
        captured_at=captured_at,
        source_width=1920,
        source_height=1080,
        encode_image=encoded_image,
    )


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
