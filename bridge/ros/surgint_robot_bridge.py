"""ROS 2 image bridge for one active SURGINT robot run."""

import argparse
import json
import struct
from array import array
from dataclasses import dataclass
from functools import lru_cache
from math import floor, isfinite
from threading import Condition, Lock, Thread
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from PIL import Image as PillowImage
from PIL import ImageDraw, ImageFont


ANALYSIS_INTERVAL_SECONDS = 0.2
GRID_TOLERANCE_SECONDS = 1e-12
DEFAULT_API_BASE = "http://127.0.0.1:7860"
DEFAULT_IMAGE_TOPIC = "/camera/image_raw"
DEFAULT_RESULT_TOPIC = "/surgint/robot_results"
DEFAULT_ANNOTATED_TOPIC = "/surgint_image"
SOURCE_ID = "ros2-camera"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
OUTCOME_COLORS = {
    "Recommendation": (89, 215, 176),
    "Needs review": (255, 198, 109),
}
NO_OUTCOME_COLOR = (127, 199, 255)
LABEL_TEXT_COLOR = (0, 0, 0)
LABEL_PADDING = 3


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
    skipped_no_active_run: int = 0
    post_failures: int = 0

    @property
    def skipped_images(self) -> int:
        return (
            self.skipped_busy
            + self.skipped_http_429
            + self.skipped_no_active_run
        )


class FramePostError(RuntimeError):
    def __init__(self, status_code: int | None, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code


class NoActiveRobotRun(RuntimeError):
    """The API has no non-terminal robot run to receive images."""


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


class ActiveRobotRunClient:
    """Discover and post to the current non-terminal robot run."""

    def __init__(self, api_base: str, timeout_seconds: float = 10.0) -> None:
        self._api_base = api_base.rstrip("/")
        self._active_url = f"{self._api_base}/v1/robot-runs/active"
        self._timeout_seconds = timeout_seconds
        self._client: RobotRunClient | None = None

    def _discover(self) -> RobotRunClient:
        request = Request(self._active_url, method="GET")
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                raise NoActiveRobotRun("no active robot run") from error
            detail = error.read().decode("utf-8", errors="replace")
            raise FramePostError(error.code, detail) from error
        except URLError as error:
            raise FramePostError(None, str(error.reason)) from error
        try:
            run_id = UUID(payload["status"]["run_id"])
        except (KeyError, TypeError, ValueError) as error:
            raise FramePostError(None, "active-run response has no valid run id") from error
        return RobotRunClient(self._api_base, run_id, self._timeout_seconds)

    def post_frame(self, **frame) -> str:
        if self._client is None:
            self._client = self._discover()
        try:
            return self._client.post_frame(**frame)
        except FramePostError as error:
            if error.status_code in {404, 409}:
                self._client = None
                raise NoActiveRobotRun("active robot run ended") from error
            raise


class FrameBridge:
    """Apply selection and run at most one frame request in a background thread."""

    def __init__(
        self,
        post_frame: Callable[..., str],
        publish_response: Callable[[str], None],
        report_error: Callable[[str], None] | None = None,
        publish_annotation: Callable[[str, object], None] | None = None,
    ) -> None:
        self._post_frame = post_frame
        self._publish_response = publish_response
        self._report_error = report_error or (lambda _message: None)
        self._publish_annotation = publish_annotation
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
        source_image: object = None,
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
                "source_image": source_image,
            },
            name="surgint-robot-frame-post",
            daemon=True,
        )
        with self._lock:
            self._worker = worker
        worker.start()
        return True

    def _send(self, source_image: object = None, **frame) -> None:
        try:
            payload = self._post_frame(**frame)
            self._publish_response(payload)
            with self._lock:
                self.stats.posted_images += 1
                self.stats.published_responses += 1
            self._annotate(payload, source_image)
        except NoActiveRobotRun:
            with self._lock:
                self.stats.skipped_no_active_run += 1
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

    def _annotate(self, payload: str, source_image: object) -> None:
        if self._publish_annotation is None or source_image is None:
            return
        try:
            self._publish_annotation(payload, source_image)
        except Exception as error:
            self._report_error(f"annotation failed: {error}")

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


class HandlingOutcomes:
    """Handling outcome of every resolved item in the current robot run."""

    def __init__(self) -> None:
        self._run_id: str | None = None
        self._outcomes: dict[int, tuple[str, str | None]] = {}

    def update(self, response: dict) -> None:
        run_id = response["status"]["run_id"]
        if run_id != self._run_id:
            self._run_id = run_id
            self._outcomes = {}
        for result in response["new_results"]:
            self._outcomes[result["item_id"]] = (
                result["handling_outcome"],
                result["action"],
            )

    def get(self, item_id: int) -> tuple[str, str | None] | None:
        return self._outcomes.get(item_id)


@lru_cache(maxsize=4)
def _label_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _rgb_image(message) -> PillowImage.Image:
    width = int(message.width)
    height = int(message.height)
    step = int(message.step)
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    modes = {"rgb8": ("RGB", "RGB"), "bgr8": ("RGB", "BGR"), "mono8": ("L", "L")}
    if message.encoding not in modes:
        raise ValueError(f"unsupported sensor_msgs/Image encoding: {message.encoding}")
    mode, raw_mode = modes[message.encoding]
    data = bytes(message.data)
    if len(data) < step * height:
        raise ValueError("image data is shorter than its declared dimensions")
    image = PillowImage.frombytes(mode, (width, height), data, "raw", raw_mode, step)
    return image.convert("RGB")


def annotate_sensor_image(message, response: dict, outcomes: HandlingOutcomes) -> bytes:
    """Draw each tracked box with its label, confidence, and handling outcome as rgb8."""
    image = _rgb_image(message)
    draw = ImageDraw.Draw(image)
    font = _label_font(max(12, image.height // 40))
    line_width = max(2, image.height // 360)
    for detection in response["detections"]:
        # A robot item ID is the track ID that resolved the item.
        outcome = outcomes.get(detection["track_id"])
        if outcome is None:
            color, status = NO_OUTCOME_COLOR, "no outcome"
        else:
            handling_outcome, action = outcome
            color = OUTCOME_COLORS[handling_outcome]
            status = action if handling_outcome == "Recommendation" else handling_outcome
        x1, y1, x2, y2 = detection["box"]
        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)

        text = (
            f"#{detection['track_id']} {detection['label']} {detection['score']:.2f}\n"
            f"{status}"
        )
        left, top, right, bottom = draw.multiline_textbbox((0, 0), text, font=font)
        label_width = right - left + 2 * LABEL_PADDING
        label_height = bottom - top + 2 * LABEL_PADDING
        label_x = min(max(x1, 0), max(image.width - label_width, 0))
        label_y = y1 - label_height if y1 >= label_height else max(y1, 0)
        draw.rectangle(
            (label_x, label_y, label_x + label_width, label_y + label_height),
            fill=color,
        )
        draw.multiline_text(
            (label_x + LABEL_PADDING - left, label_y + LABEL_PADDING - top),
            text,
            fill=LABEL_TEXT_COLOR,
            font=font,
        )
    return image.tobytes()


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        type=UUID,
        help="fixed robot run; omit to discover the current active run",
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--image-topic", default=DEFAULT_IMAGE_TOPIC)
    parser.add_argument("--result-topic", default=DEFAULT_RESULT_TOPIC)
    parser.add_argument("--annotated-topic", default=DEFAULT_ANNOTATED_TOPIC)
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> None:
    args, ros_args = parse_args(argv)

    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from std_msgs.msg import String

    rclpy.init(args=ros_args)

    class SurgintRobotBridgeNode(Node):
        def __init__(self) -> None:
            super().__init__("surgint_robot_image_bridge")
            self._result_publisher = self.create_publisher(String, args.result_topic, 10)
            self._annotated_publisher = self.create_publisher(
                Image,
                args.annotated_topic,
                2,
            )
            self._outcomes = HandlingOutcomes()
            if args.run_id is None:
                client = ActiveRobotRunClient(args.api_base)
                run_target = "the current active run"
            else:
                client = RobotRunClient(args.api_base, args.run_id)
                run_target = f"run {args.run_id}"
            self._bridge = FrameBridge(
                client.post_frame,
                self._publish_response,
                self.get_logger().error,
                self._publish_annotation,
            )
            self._source_sequence = 0
            self._subscription = self.create_subscription(
                Image,
                args.image_topic,
                self._on_image,
                qos_profile_sensor_data,
            )
            self.get_logger().info(
                f"bridging {args.image_topic} to {run_target}; "
                f"publishing responses on {args.result_topic} "
                f"and annotated images on {args.annotated_topic}"
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
                source_image=message,
            )

        def _publish_response(self, payload: str) -> None:
            self._result_publisher.publish(String(data=payload))

        def _publish_annotation(self, payload: str, message: Image) -> None:
            response = json.loads(payload)
            self._outcomes.update(response)
            if self._annotated_publisher.get_subscription_count() == 0:
                return
            annotated = Image()
            annotated.header = message.header
            annotated.height = message.height
            annotated.width = message.width
            annotated.encoding = "rgb8"
            annotated.step = message.width * 3
            annotated.data = array(
                "B",
                annotate_sensor_image(message, response, self._outcomes),
            )
            self._annotated_publisher.publish(annotated)

        def destroy_node(self) -> bool:
            self._bridge.close()
            stats = self._bridge.stats
            totals = (
                "bridge totals: "
                f"received={stats.received_images} selections={stats.selections} "
                f"posted={stats.posted_images} skipped={stats.skipped_images} "
                f"skipped_busy={stats.skipped_busy} "
                f"skipped_http_429={stats.skipped_http_429} "
                f"skipped_no_active_run={stats.skipped_no_active_run} "
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
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
