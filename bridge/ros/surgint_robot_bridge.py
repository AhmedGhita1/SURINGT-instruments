"""ROS 2 image bridge for one active SURGINT robot run."""

import argparse
import json
import struct
from dataclasses import dataclass
from math import floor, isfinite
from threading import Condition, Lock, Thread
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4


ANALYSIS_INTERVAL_SECONDS = 0.2
GRID_TOLERANCE_SECONDS = 1e-12
DEFAULT_API_BASE = "http://127.0.0.1:7860"
DEFAULT_IMAGE_TOPIC = "/camera/image_raw"
DEFAULT_RESULT_TOPIC = "/surgint/robot_results"
SOURCE_ID = "ros2-camera"


class SourceTimeSelector:
    """Select the first image at or after each 0.2-second source-time deadline."""

    def __init__(self) -> None:
        self._grid_start: float | None = None
        self._grid_index = 0

    def select(self, captured_at: float) -> bool:
        if not isfinite(captured_at) or captured_at < 0.0:
            raise ValueError("image header timestamp must be finite and non-negative")
        if self._grid_start is None:
            self._grid_start = captured_at
        due = captured_at + GRID_TOLERANCE_SECONDS - self._grid_start
        if due < self._grid_index * ANALYSIS_INTERVAL_SECONDS:
            return False
        self._grid_index = floor(due / ANALYSIS_INTERVAL_SECONDS) + 1
        return True


@dataclass
class BridgeStats:
    received_images: int = 0
    selections: int = 0
    posted_images: int = 0
    published_responses: int = 0
    skipped_busy: int = 0
    skipped_http_429: int = 0
    post_failures: int = 0

    @property
    def skipped_images(self) -> int:
        return self.skipped_busy + self.skipped_http_429


class FramePostError(RuntimeError):
    def __init__(self, status_code: int | None, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code


def _multipart_body(
    fields: dict[str, str],
    image: bytes,
    image_filename: str,
    image_content_type: str,
) -> tuple[bytes, str]:
    boundary = f"surgint-{uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            (
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            )
        )
    chunks.extend(
        (
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="image"; '
                f'filename="{image_filename}"\r\n'
            ).encode(),
            f"Content-Type: {image_content_type}\r\n\r\n".encode(),
            image,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        )
    )
    return b"".join(chunks), boundary


class RobotRunClient:
    def __init__(self, api_base: str, run_id: UUID, timeout_seconds: float = 10.0) -> None:
        self._url = f"{api_base.rstrip('/')}/v1/robot-runs/{run_id}/frames"
        self._timeout_seconds = timeout_seconds

    def post_frame(
        self,
        *,
        source_sequence: int,
        captured_at: float,
        source_width: int,
        source_height: int,
        image: bytes,
        image_filename: str,
        image_content_type: str,
    ) -> str:
        fields = {
            "schema_version": "1.1",
            "source_id": SOURCE_ID,
            "sequence": str(source_sequence),
            "captured_at": str(captured_at),
            "source_width": str(source_width),
            "source_height": str(source_height),
        }
        body, boundary = _multipart_body(
            fields,
            image,
            image_filename,
            image_content_type,
        )
        request = Request(
            self._url,
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise FramePostError(error.code, detail) from error
        except URLError as error:
            raise FramePostError(None, str(error.reason)) from error
        json.loads(payload)
        return payload


class FrameBridge:
    """Apply selection and run at most one frame request in a background thread."""

    def __init__(
        self,
        post_frame: Callable[..., str],
        publish_response: Callable[[str], None],
        report_error: Callable[[str], None] | None = None,
    ) -> None:
        self._post_frame = post_frame
        self._publish_response = publish_response
        self._report_error = report_error or (lambda _message: None)
        self._selector = SourceTimeSelector()
        self._lock = Lock()
        self._idle = Condition(self._lock)
        self._busy = False
        self._closed = False
        self._worker: Thread | None = None
        self.stats = BridgeStats()

    def offer(
        self,
        *,
        source_sequence: int,
        captured_at: float,
        source_width: int,
        source_height: int,
        encode_image: Callable[[], tuple[bytes, str, str]],
    ) -> bool:
        with self._lock:
            if self._closed:
                return False
            self.stats.received_images += 1
            if not self._selector.select(captured_at):
                return False
            self.stats.selections += 1
            if self._busy:
                self.stats.skipped_busy += 1
                return False
            self._busy = True

        try:
            image, image_filename, image_content_type = encode_image()
        except Exception as error:
            with self._lock:
                self.stats.post_failures += 1
                self._busy = False
                self._idle.notify_all()
            self._report_error(f"image encoding failed: {error}")
            return False

        worker = Thread(
            target=self._send,
            kwargs={
                "source_sequence": source_sequence,
                "captured_at": captured_at,
                "source_width": source_width,
                "source_height": source_height,
                "image": image,
                "image_filename": image_filename,
                "image_content_type": image_content_type,
            },
            name="surgint-robot-frame-post",
            daemon=True,
        )
        with self._lock:
            self._worker = worker
        worker.start()
        return True

    def _send(self, **frame) -> None:
        try:
            payload = self._post_frame(**frame)
            self._publish_response(payload)
            with self._lock:
                self.stats.posted_images += 1
                self.stats.published_responses += 1
        except FramePostError as error:
            with self._lock:
                if error.status_code == 429:
                    self.stats.skipped_http_429 += 1
                else:
                    self.stats.post_failures += 1
            if error.status_code != 429:
                self._report_error(f"frame post failed: {error}")
        except Exception as error:
            with self._lock:
                self.stats.post_failures += 1
            self._report_error(f"frame post failed: {error}")
        finally:
            with self._lock:
                self._busy = False
                self._idle.notify_all()

    def wait_until_idle(self, timeout: float | None = None) -> bool:
        with self._idle:
            return self._idle.wait_for(lambda: not self._busy, timeout=timeout)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.wait_until_idle()


def _packed_rows(data: bytes, height: int, step: int, row_bytes: int) -> bytes:
    if step < row_bytes or len(data) < step * height:
        raise ValueError("image data is shorter than its declared dimensions")
    if step == row_bytes:
        return data[: row_bytes * height]
    return b"".join(data[offset : offset + row_bytes] for offset in range(0, step * height, step))


def encode_sensor_image(message) -> tuple[bytes, str, str]:
    """Encode common 8-bit sensor_msgs/Image layouts with only the standard library."""
    width = int(message.width)
    height = int(message.height)
    step = int(message.step)
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    data = bytes(message.data)
    if message.encoding == "rgb8":
        pixels = _packed_rows(data, height, step, width * 3)
        return (
            f"P6\n{width} {height}\n255\n".encode() + pixels,
            "frame.ppm",
            "image/x-portable-pixmap",
        )
    if message.encoding == "mono8":
        pixels = _packed_rows(data, height, step, width)
        return (
            f"P5\n{width} {height}\n255\n".encode() + pixels,
            "frame.pgm",
            "image/x-portable-graymap",
        )
    if message.encoding == "bgr8":
        row_bytes = width * 3
        packed = _packed_rows(data, height, step, row_bytes)
        bmp_step = (row_bytes + 3) & ~3
        padding = b"\0" * (bmp_step - row_bytes)
        pixels = b"".join(
            packed[offset : offset + row_bytes] + padding
            for offset in range(0, len(packed), row_bytes)
        )
        image_size = len(pixels)
        header = struct.pack("<2sIHHI", b"BM", 54 + image_size, 0, 0, 54)
        header += struct.pack(
            "<IiiHHIIiiII",
            40,
            width,
            -height,
            1,
            24,
            0,
            image_size,
            2835,
            2835,
            0,
            0,
        )
        return header + pixels, "frame.bmp", "image/bmp"
    raise ValueError(f"unsupported sensor_msgs/Image encoding: {message.encoding}")


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--image-topic", default=DEFAULT_IMAGE_TOPIC)
    parser.add_argument("--result-topic", default=DEFAULT_RESULT_TOPIC)
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> None:
    args, ros_args = parse_args(argv)

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from std_msgs.msg import String

    rclpy.init(args=ros_args)

    class SurgintRobotBridgeNode(Node):
        def __init__(self) -> None:
            super().__init__("surgint_robot_image_bridge")
            self._result_publisher = self.create_publisher(String, args.result_topic, 10)
            client = RobotRunClient(args.api_base, args.run_id)
            self._bridge = FrameBridge(
                client.post_frame,
                self._publish_response,
                self.get_logger().error,
            )
            self._source_sequence = 0
            self._subscription = self.create_subscription(
                Image,
                args.image_topic,
                self._on_image,
                qos_profile_sensor_data,
            )
            self.get_logger().info(
                f"bridging {args.image_topic} to run {args.run_id}; "
                f"publishing responses on {args.result_topic}"
            )

        def _on_image(self, message: Image) -> None:
            source_sequence = self._source_sequence
            self._source_sequence += 1
            captured_at = message.header.stamp.sec + message.header.stamp.nanosec / 1e9
            self._bridge.offer(
                source_sequence=source_sequence,
                captured_at=captured_at,
                source_width=message.width,
                source_height=message.height,
                encode_image=lambda: encode_sensor_image(message),
            )

        def _publish_response(self, payload: str) -> None:
            self._result_publisher.publish(String(data=payload))

        def destroy_node(self) -> bool:
            self._bridge.close()
            stats = self._bridge.stats
            totals = (
                "bridge totals: "
                f"received={stats.received_images} selections={stats.selections} "
                f"posted={stats.posted_images} skipped={stats.skipped_images} "
                f"skipped_busy={stats.skipped_busy} "
                f"skipped_http_429={stats.skipped_http_429} "
                f"failures={stats.post_failures}"
            )
            if rclpy.ok():
                self.get_logger().info(totals)
            else:
                print(totals)
            return super().destroy_node()

    node = SurgintRobotBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
