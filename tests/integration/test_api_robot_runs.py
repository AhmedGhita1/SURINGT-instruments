from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import numpy as np
import torch
from fastapi.testclient import TestClient
from PIL import Image

from services.api.app import create_app
from services.api.settings import ServingSettings
from surgint.model import Detections


class FakeClock:
    def __init__(self, now: float = 10.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class FakeDetector:
    def __init__(self) -> None:
        self.manifest = SimpleNamespace(
            labels=("scalpel", "forceps"),
            input_size=(640, 640),
            pad_color=114,
            rescale_factor=1 / 255,
            weights_sha256="sha256:" + "a" * 64,
        )

    def to(self, device: str) -> None:
        pass

    def eval(self) -> None:
        pass

    def predict(self, pixel_values):
        batch_size = len(pixel_values)
        logits = torch.full((batch_size, 1, 2), -10.0)
        logits[:, :, 0] = 10.0
        boxes = torch.tensor([[[0.5, 0.5, 0.25, 0.25]]], dtype=torch.float32)
        return logits, boxes.repeat(batch_size, 1, 1)


def test_robot_run_lifecycle_exports_summary_and_restarts_in_isolation(
    monkeypatch,
) -> None:
    clock = FakeClock()
    monkeypatch.setattr("services.api.app.perf_counter", clock)
    detector = FakeDetector()
    application = create_app(
        ServingSettings(checkpoint=Path("model")),
        lambda _: detector,
    )

    with TestClient(application) as client:
        started = client.post("/v1/robot-runs", json=start_request())
        assert started.status_code == 201
        run_id = UUID(started.json()["status"]["run_id"])
        first_run = application.state.robot_runs.get(run_id)
        assert started.json()["status"]["state"] == "active"
        assert started.json()["results"] == []
        assert first_run.pipeline.detector is detector

        conflict = client.post("/v1/robot-runs", json=start_request())
        assert conflict.status_code == 409
        assert "release" in conflict.json()["detail"]

        first_run.pipeline.predict = Mock(
            return_value=tracked_detections([0], [7], [0.91])
        )
        frame_response = post_frame(client, run_id, sequence=0, captured_at=1.0)
        assert frame_response.status_code == 200
        frame_payload = frame_response.json()
        assert frame_payload["frame"]["source_id"] == "robot-camera"
        assert frame_payload["status"]["result_count"] == 1
        assert frame_payload["new_results"][0]["item_id"] == 7
        assert frame_payload["new_results"][0]["handling_outcome"] == "Recommendation"
        assert frame_payload["new_inventory_entries"][0]["item_id"] == 7

        state = client.get(f"/v1/robot-runs/{run_id}")
        assert state.status_code == 200
        assert state.json()["results"] == frame_payload["new_results"]
        assert state.json()["inventory"] == frame_payload["new_inventory_entries"]

        before_stop = client.get(f"/v1/robot-runs/{run_id}/summary")
        assert before_stop.status_code == 409

        clock.now = 10.5
        stopped = client.post(f"/v1/robot-runs/{run_id}/stop")
        assert stopped.status_code == 200
        assert stopped.json()["state"] == "stopped"
        assert stopped.json()["frame_count"] == 1

        rejected = post_frame(client, run_id, sequence=1, captured_at=1.2)
        assert rejected.status_code == 409
        assert rejected.json() == {"detail": "robot run is stopped"}

        summary = client.get(f"/v1/robot-runs/{run_id}/summary")
        assert summary.json() == stopped.json()
        exported = client.get(f"/v1/robot-runs/{run_id}/export")
        assert exported.status_code == 200
        assert exported.json() == stopped.json()
        assert "attachment" in exported.headers["content-disposition"]
        assert "Not for clinical use" in exported.json()["research_warning"]

        assert client.delete(f"/v1/robot-runs/{run_id}").status_code == 204
        restarted = client.post("/v1/robot-runs", json=start_request())
        assert restarted.status_code == 201
        restarted_id = UUID(restarted.json()["status"]["run_id"])
        restarted_run = application.state.robot_runs.get(restarted_id)
        assert restarted_id != run_id
        assert restarted_run.pipeline is not first_run.pipeline
        assert restarted_run.pipeline.tracker is not first_run.pipeline.tracker
        assert restarted_run.pipeline.detector is first_run.pipeline.detector
        assert restarted.json()["status"]["frame_count"] == 0
        assert restarted.json()["results"] == []


def test_robot_run_requires_readiness_and_recoverable_input_stays_active() -> None:
    with TestClient(create_app(ServingSettings(checkpoint=None))) as client:
        assert client.post("/v1/robot-runs", json=start_request()).status_code == 503

    application = create_app(
        ServingSettings(checkpoint=Path("model")),
        lambda _: FakeDetector(),
    )
    with TestClient(application) as client:
        run_id = start_run(client)
        invalid = client.post(
            f"/v1/robot-runs/{run_id}/frames",
            files={"image": ("frame.png", b"not an image", "image/png")},
            data=frame_form(0, 0.0),
        )
        assert invalid.status_code == 400

        missing_metadata = client.post(
            f"/v1/robot-runs/{run_id}/frames",
            files={"image": ("frame.png", image_bytes(), "image/png")},
        )
        assert missing_metadata.status_code == 422
        state = client.get(f"/v1/robot-runs/{run_id}").json()["status"]
        assert state["state"] == "active"
        assert state["frame_count"] == 0
        assert state["failure"] is None


def test_robot_run_rejects_a_busy_frame_without_queueing() -> None:
    application = create_app(
        ServingSettings(checkpoint=Path("model")),
        lambda _: FakeDetector(),
    )

    with TestClient(application) as client:
        run_id = start_run(client)
        run = application.state.robot_runs.get(run_id)
        processing = Event()
        release = Event()

        def slow_predict(*_args, **_kwargs):
            processing.set()
            release.wait(5)
            return tracked_detections([], [], [])

        run.pipeline.predict = Mock(side_effect=slow_predict)
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(post_frame, client, run_id, 0, 0.0)
            assert processing.wait(5)
            second = post_frame(client, run_id, 1, 0.2)
            release.set()
            first = first.result(timeout=5)

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json() == {"detail": "robot run is already processing a frame"}
        assert run.pipeline.predict.call_count == 1
        assert client.get(f"/v1/robot-runs/{run_id}").json()["status"]["frame_count"] == 1


def test_robot_run_exposes_degraded_stream_and_recovers(monkeypatch) -> None:
    clock = FakeClock()
    monkeypatch.setattr("services.api.app.perf_counter", clock)
    application = create_app(
        ServingSettings(checkpoint=Path("model")),
        lambda _: FakeDetector(),
    )

    with TestClient(application) as client:
        run_id = start_run(client)
        clock.now = 11.0
        degraded = client.get(f"/v1/robot-runs/{run_id}").json()["status"]
        assert degraded["state"] == "degraded"
        assert degraded["timing_condition"] == "image-stream-stopped"

        clock.now = 11.1
        recovered = post_frame(client, run_id, 0, 0.0)
        assert recovered.status_code == 200
        assert recovered.json()["status"]["state"] == "active"
        assert recovered.json()["status"]["timing_condition"] == "current"


def test_critical_robot_frame_failure_is_terminal_and_releasable() -> None:
    application = create_app(
        ServingSettings(checkpoint=Path("model")),
        lambda _: FakeDetector(),
    )

    with TestClient(application) as client:
        run_id = start_run(client)
        run = application.state.robot_runs.get(run_id)
        run.pipeline.predict = Mock(side_effect=RuntimeError("GPU failed"))

        failed = post_frame(client, run_id, 0, 0.0)
        assert failed.status_code == 500
        assert failed.json() == {"detail": "robot run failed during frame processing"}

        state = client.get(f"/v1/robot-runs/{run_id}").json()["status"]
        assert state["state"] == "failed"
        assert "release this run" in state["failure"]
        assert post_frame(client, run_id, 1, 0.2).status_code == 409
        assert client.get(f"/v1/robot-runs/{run_id}/export").status_code == 409
        assert client.delete(f"/v1/robot-runs/{run_id}").status_code == 204
        assert client.post("/v1/robot-runs", json=start_request()).status_code == 201


def start_run(client: TestClient) -> UUID:
    response = client.post("/v1/robot-runs", json=start_request())
    assert response.status_code == 201
    return UUID(response.json()["status"]["run_id"])


def start_request() -> dict[str, str]:
    return {
        "workflow_stage": "post-procedure-clearing",
        "contamination_state": "not-regulated",
        "lifecycle": "reusable",
    }


def post_frame(
    client: TestClient,
    run_id: UUID,
    sequence: int,
    captured_at: float,
):
    return client.post(
        f"/v1/robot-runs/{run_id}/frames",
        files={"image": ("frame.png", image_bytes(), "image/png")},
        data=frame_form(sequence, captured_at),
    )


def image_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (12, 8), color="black").save(stream, format="PNG")
    return stream.getvalue()


def frame_form(sequence: int, captured_at: float) -> dict[str, str]:
    return {
        "schema_version": "1.1",
        "source_id": "robot-camera",
        "sequence": str(sequence),
        "captured_at": str(captured_at),
        "source_width": "12",
        "source_height": "8",
    }


def tracked_detections(class_ids, track_ids, scores) -> Detections:
    count = len(track_ids)
    return Detections(
        boxes=np.zeros((count, 4), dtype=np.float32),
        scores=np.asarray(scores, dtype=np.float32),
        class_ids=np.asarray(class_ids, dtype=np.int64),
        track_ids=np.asarray(track_ids, dtype=np.int64),
    )
