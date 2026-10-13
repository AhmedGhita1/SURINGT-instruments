"""Measure the existing sequential frame path without changing its scheduler."""

import argparse
import io
import json
import os
import platform
from pathlib import Path
from time import perf_counter, sleep

import numpy as np
import torch
from fastapi.testclient import TestClient
from PIL import Image

from services.api.app import create_app
from services.api.settings import ServingSettings
from surgint.dataset.coco import SurgintDataset
from surgint.evaluation.inventory import inventory_counts, inventory_evaluate
from surgint.evaluation.mot import mot_counts, mot_evaluate
from surgint.model import Detections
from surgint.runtime.inventory import Inventory

SERVER_PHASES = (
    "receive",
    "decode",
    "queue",
    "preprocess",
    "inference",
    "postprocess",
    "tracking",
    "inventory",
    "server",
)


def parse_server_timing(value: str) -> dict[str, float]:
    """Parse duration values from the API's Server-Timing header."""
    result = {}
    for entry in value.split(","):
        parts = [part.strip() for part in entry.split(";")]
        duration = next((part[4:] for part in parts[1:] if part.startswith("dur=")), None)
        if parts[0] and duration is not None:
            result[parts[0]] = float(duration)
    return result


def selection_indices(
    frame_count: int,
    source_fps: float,
    detector_fps: float,
    duration_seconds: float,
) -> list[int]:
    """Select the first source frame at or after each detector deadline."""
    limit = min(frame_count, int(np.ceil(duration_seconds * source_fps)))
    selected = []
    deadline = 0.0
    for index in range(limit):
        timestamp = index / source_fps
        if timestamp + 1e-12 >= deadline:
            selected.append(index)
            deadline += 1.0 / detector_fps
    return selected


def simulate_sequential_scheduler(
    service_ms: list[float],
    detector_fps: float,
    display_fps: float,
    duration_seconds: float,
) -> dict:
    """Replay the existing no-pending-work policy over measured service times."""
    if not service_ms:
        raise ValueError("service_ms must not be empty")

    candidates = np.arange(0.0, duration_seconds, 1.0 / detector_fps)
    admissions = []
    busy_until = -1.0
    for candidate in candidates:
        if candidate + 1e-12 < busy_until:
            continue
        service = service_ms[len(admissions) % len(service_ms)] / 1000.0
        busy_until = float(candidate) + service
        admissions.append((float(candidate), busy_until))

    overlay_ages = []
    completed = -1
    for displayed_at in np.arange(0.0, duration_seconds, 1.0 / display_fps):
        while completed + 1 < len(admissions) and admissions[completed + 1][1] <= displayed_at:
            completed += 1
        if completed >= 0:
            overlay_ages.append((float(displayed_at) - admissions[completed][0]) * 1000.0)

    admitted = len(admissions)
    return {
        "candidate_frames": int(len(candidates)),
        "admitted_frames": admitted,
        "busy_source_frames": int(len(candidates) - admitted),
        "overwritten_frames": 0,
        "effective_detector_fps": admitted / duration_seconds,
        "bounded_pending_frames": 0,
        "overlay_age_ms": summarize(overlay_ages),
    }


def simulate_latest_frame_scheduler(
    service_ms: list[float],
    detector_fps: float,
    display_fps: float,
    duration_seconds: float,
) -> dict:
    """Replay one in-flight request plus one replaceable newest pending frame."""
    if not service_ms:
        raise ValueError("service_ms must not be empty")
    if detector_fps <= 0.0 or display_fps <= 0.0 or duration_seconds <= 0.0:
        raise ValueError("rates and duration must be positive")

    candidates = [float(value) for value in np.arange(0.0, duration_seconds, 1.0 / detector_fps)]
    admissions: list[tuple[float, float]] = []
    pending: float | None = None
    busy_until: float | None = None
    busy_observations = 0
    overwritten = 0
    max_pending = 0

    def launch(captured_at: float, launched_at: float) -> None:
        nonlocal busy_until
        service = service_ms[len(admissions) % len(service_ms)] / 1000.0
        busy_until = launched_at + service
        admissions.append((captured_at, busy_until))

    for candidate in candidates:
        while busy_until is not None and busy_until <= candidate + 1e-12:
            completed_at = busy_until
            busy_until = None
            if pending is not None:
                next_capture = pending
                pending = None
                launch(next_capture, completed_at)
        if busy_until is None:
            launch(candidate, candidate)
            continue
        busy_observations += 1
        if pending is not None:
            overwritten += 1
        pending = candidate
        max_pending = max(max_pending, 1)

    shutdown_drops = int(pending is not None)
    pending = None
    overlay_ages = []
    completed = -1
    for displayed_at in np.arange(0.0, duration_seconds, 1.0 / display_fps):
        while completed + 1 < len(admissions) and admissions[completed + 1][1] <= displayed_at:
            completed += 1
        if completed >= 0:
            overlay_ages.append((float(displayed_at) - admissions[completed][0]) * 1000.0)

    return {
        "candidate_frames": len(candidates),
        "admitted_frames": len(admissions),
        "admitted_capture_times": [captured_at for captured_at, _ in admissions],
        "busy_source_frames": busy_observations,
        "overwritten_frames": overwritten,
        "shutdown_drops": shutdown_drops,
        "effective_detector_fps": len(admissions) / duration_seconds,
        "bounded_pending_frames": max_pending,
        "overlay_age_ms": summarize(overlay_ages),
    }


def replay_overlay_age(
    admissions: list[tuple[float, float]],
    display_fps: float,
    duration_seconds: float,
) -> dict:
    """Replay held-result age on a display clock from actual capture and result times."""
    overlay_ages = []
    completed = -1
    for displayed_at in np.arange(0.0, duration_seconds, 1.0 / display_fps):
        while completed + 1 < len(admissions) and admissions[completed + 1][1] <= displayed_at:
            completed += 1
        if completed >= 0:
            overlay_ages.append((float(displayed_at) - admissions[completed][0]) * 1000.0)
    return summarize(overlay_ages)


def summarize(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "max": None}
    samples = np.asarray(values, dtype=float)
    return {
        "count": int(len(samples)),
        "mean": float(samples.mean()),
        "p50": float(np.percentile(samples, 50)),
        "p95": float(np.percentile(samples, 95)),
        "max": float(samples.max()),
    }


def detections_from_response(entries: list[dict]) -> Detections:
    return Detections(
        boxes=np.asarray([entry["box"] for entry in entries], dtype=np.float32).reshape(-1, 4),
        scores=np.asarray([entry["score"] for entry in entries], dtype=np.float32),
        class_ids=np.asarray([entry["class_id"] for entry in entries], dtype=np.int64),
        track_ids=np.asarray([entry["track_id"] for entry in entries], dtype=np.int64),
    )


def encode_jpeg(frame: np.ndarray) -> bytes:
    stream = io.BytesIO()
    Image.fromarray(frame).save(stream, format="JPEG", quality=90)
    return stream.getvalue()


def temporal_form(
    source_id: str,
    sequence: int,
    captured_at: float,
    frame: np.ndarray,
) -> dict[str, str]:
    """Build the complete versioned temporal form contract for one frame."""
    return {
        "schema_version": "1.1",
        "source_id": source_id,
        "sequence": str(sequence),
        "captured_at": str(captured_at),
        "source_width": str(frame.shape[1]),
        "source_height": str(frame.shape[0]),
    }


def measure_rate(
    client: TestClient,
    dataset: SurgintDataset,
    detector_fps: float,
    source_fps: float,
    display_fps: float,
    duration_seconds: float,
    class_count: int,
) -> dict:
    session_id = client.post("/v1/sessions").json()["session_id"]
    indices = selection_indices(len(dataset), source_fps, detector_fps, duration_seconds)
    phase_samples: dict[str, list[float]] = {
        name: []
        for name in (
            "capture_encode",
            "receive",
            "decode",
            "queue",
            "preprocess",
            "inference",
            "postprocess",
            "tracking",
            "inventory",
            "server",
            "response_client_boundary",
            "capture_to_result",
        )
    }
    inventory = Inventory()
    mot_frames = []
    inventory_frames = []
    first_confirmed_sample = None

    for sample_number, index in enumerate(indices):
        sample = dataset[index]
        phase_started_at = perf_counter()
        encoded = encode_jpeg(sample["frame"])
        capture_encode_ms = (perf_counter() - phase_started_at) * 1000.0

        request_started_at = perf_counter()
        response = client.post(
            f"/v1/sessions/{session_id}/frames",
            files={"image": ("frame.jpg", encoded, "image/jpeg")},
            data=temporal_form(
                f"measure:{session_id}",
                sample_number,
                index / source_fps,
                sample["frame"],
            ),
        )
        request_ms = (perf_counter() - request_started_at) * 1000.0
        response.raise_for_status()

        server = parse_server_timing(response.headers["server-timing"])
        payload = response.json()
        detections = detections_from_response(payload["detections"])
        inventory.update(detections)
        if first_confirmed_sample is None and len(detections.boxes):
            first_confirmed_sample = sample_number

        phase_samples["capture_encode"].append(capture_encode_ms)
        for name in SERVER_PHASES:
            phase_samples[name].append(server[name])
        phase_samples["response_client_boundary"].append(max(0.0, request_ms - server["server"]))
        phase_samples["capture_to_result"].append(capture_encode_ms + request_ms)

        mot_frames.append(
            (
                sample["boxes"],
                sample["track_ids"],
                sample["class_ids"],
                detections.boxes,
                detections.track_ids,
                detections.class_ids,
            )
        )
        inventory_frames.append((sample["instance_uids"], sample["class_ids"]))

    predicted_inventory = inventory.finalize().counts()
    inventory_result = inventory_evaluate(
        inventory_counts(inventory_frames, predicted_inventory, tuple(range(class_count)))
    )
    tracking_result = mot_evaluate(mot_counts(mot_frames, iou_threshold=0.5))
    capture_to_result = phase_samples["capture_to_result"]
    scheduler = simulate_sequential_scheduler(
        capture_to_result,
        detector_fps,
        display_fps,
        duration_seconds,
    )
    interval_ms = 1000.0 / detector_fps
    latency = summarize(capture_to_result)

    confirmation = None
    if first_confirmed_sample is not None:
        confirmation = {
            "selected_sample": first_confirmed_sample + 1,
            "nominal_source_delay_ms": indices[first_confirmed_sample] / source_fps * 1000.0,
            "sequential_wall_delay_ms": float(sum(capture_to_result[: first_confirmed_sample + 1])),
        }

    client.delete(f"/v1/sessions/{session_id}")
    return {
        "requested_detector_fps": detector_fps,
        "selected_source_frames": len(indices),
        "selection_indices": indices,
        "phase_ms": {name: summarize(values) for name, values in phase_samples.items()},
        "service_interval_ms": interval_ms,
        "p95_service_to_interval_ratio": latency["p95"] / interval_ms,
        "sustainable_without_busy_skips": scheduler["busy_source_frames"] == 0,
        "sequential_scheduler_simulation": scheduler,
        "live_first_display_overlay_age_ms": latency,
        "tracking_at_nominal_selection_rate": {
            key: tracking_result[key]
            for key in ("MOTA", "IDF1", "id_switches", "frames", "gt", "predictions", "fp", "fn")
        },
        "confirmation": confirmation,
        "inventory_at_nominal_selection_rate": {
            key: inventory_result[key]
            for key in (
                "inventory_ground_truth",
                "inventory_predictions",
                "inventory_error",
                "inventory_absolute_error",
                "inventory_mean_absolute_error",
                "class_exact_match_rate",
                "session_exact_match_rate",
            )
        },
    }


def measure_remote_rate(
    client,
    dataset: SurgintDataset,
    detector_fps: float,
    source_fps: float,
    display_fps: float,
    duration_seconds: float,
    class_count: int,
) -> dict:
    """Measure the public endpoint while pacing source candidates on wall time."""
    session_response = client.post("/v1/sessions")
    session_response.raise_for_status()
    session_id = session_response.json()["session_id"]
    indices = selection_indices(len(dataset), source_fps, detector_fps, duration_seconds)
    phase_samples: dict[str, list[float]] = {
        name: []
        for name in (
            "capture_encode",
            *SERVER_PHASES,
            "response_client_boundary",
            "capture_to_result",
        )
    }
    inventory = Inventory()
    mot_frames = []
    inventory_frames = []
    admissions: list[tuple[float, float]] = []
    first_confirmation = None
    started_at = perf_counter()

    try:
        for index in indices:
            source_time = index / source_fps
            remaining = source_time - (perf_counter() - started_at)
            if remaining > 0.0:
                sleep(remaining)
            elif admissions and remaining < -0.001:
                continue

            sample = dataset[index]
            capture_offset = perf_counter() - started_at
            phase_started_at = perf_counter()
            encoded = encode_jpeg(sample["frame"])
            capture_encode_ms = (perf_counter() - phase_started_at) * 1000.0

            request_started_at = perf_counter()
            response = client.post(
                f"/v1/sessions/{session_id}/frames",
                files={"image": ("frame.jpg", encoded, "image/jpeg")},
                data=temporal_form(
                    f"measure:{session_id}",
                    len(admissions),
                    source_time,
                    sample["frame"],
                ),
            )
            request_ms = (perf_counter() - request_started_at) * 1000.0
            response.raise_for_status()
            result_offset = perf_counter() - started_at

            server = parse_server_timing(response.headers["server-timing"])
            payload = response.json()
            detections = detections_from_response(payload["detections"])
            inventory.update(detections)
            admitted_number = len(admissions) + 1
            if first_confirmation is None and len(detections.boxes):
                first_confirmation = {
                    "selected_sample": admitted_number,
                    "source_delay_ms": source_time * 1000.0,
                    "actual_wall_delay_ms": result_offset * 1000.0,
                }

            admissions.append((capture_offset, result_offset))
            phase_samples["capture_encode"].append(capture_encode_ms)
            for name in SERVER_PHASES:
                if name not in server:
                    raise RuntimeError(f"remote response omitted Server-Timing phase {name!r}")
                phase_samples[name].append(server[name])
            phase_samples["response_client_boundary"].append(
                max(0.0, request_ms - server["server"])
            )
            phase_samples["capture_to_result"].append(capture_encode_ms + request_ms)

            mot_frames.append(
                (
                    sample["boxes"],
                    sample["track_ids"],
                    sample["class_ids"],
                    detections.boxes,
                    detections.track_ids,
                    detections.class_ids,
                )
            )
            inventory_frames.append((sample["instance_uids"], sample["class_ids"]))
    finally:
        client.delete(f"/v1/sessions/{session_id}")

    actual_elapsed = perf_counter() - started_at
    if not admissions:
        raise RuntimeError(f"no frames were admitted at {detector_fps:g} FPS")

    predicted_inventory = inventory.finalize().counts()
    inventory_result = inventory_evaluate(
        inventory_counts(inventory_frames, predicted_inventory, tuple(range(class_count)))
    )
    tracking_result = mot_evaluate(mot_counts(mot_frames, iou_threshold=0.5))
    capture_to_result = phase_samples["capture_to_result"]
    interval_ms = 1000.0 / detector_fps
    latency = summarize(capture_to_result)
    admitted = len(admissions)
    busy = len(indices) - admitted

    return {
        "requested_detector_fps": detector_fps,
        "candidate_source_frames": len(indices),
        "admitted_source_frames": admitted,
        "phase_ms": {name: summarize(values) for name, values in phase_samples.items()},
        "service_interval_ms": interval_ms,
        "p95_service_to_interval_ratio": latency["p95"] / interval_ms,
        "sustainable_without_busy_skips": busy == 0,
        "actual_sequential_scheduler": {
            "candidate_frames": len(indices),
            "admitted_frames": admitted,
            "busy_source_frames": busy,
            "overwritten_frames": 0,
            "bounded_pending_frames": 0,
            "effective_detector_fps": admitted / duration_seconds,
            "completion_rate_fps": admitted / actual_elapsed,
            "measurement_wall_seconds": actual_elapsed,
            "overlay_age_ms": replay_overlay_age(admissions, display_fps, duration_seconds),
        },
        "live_first_display_overlay_age_proxy_ms": latency,
        "tracking_at_actual_admitted_rate": {
            key: tracking_result[key]
            for key in ("MOTA", "IDF1", "id_switches", "frames", "gt", "predictions", "fp", "fn")
        },
        "confirmation": first_confirmation,
        "inventory_at_actual_admitted_rate": {
            key: inventory_result[key]
            for key in (
                "inventory_ground_truth",
                "inventory_predictions",
                "inventory_error",
                "inventory_absolute_error",
                "inventory_mean_absolute_error",
                "class_exact_match_rate",
                "session_exact_match_rate",
            )
        },
    }


def machine_profile(device: str) -> dict:
    return {
        "platform": platform.platform(),
        "processor": processor_name(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "cuda_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def processor_name() -> str:
    """Return the Windows CPU brand when available, with a portable fallback."""
    if platform.system() == "Windows":
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    return platform.processor()


def run(args: argparse.Namespace) -> dict:
    dataset = SurgintDataset(args.data_root, f"eval/{args.session}", "detection-tracking")
    application = create_app(
        ServingSettings(checkpoint=args.checkpoint, device=args.device, nms_iou=args.nms_iou)
    )

    with TestClient(application) as client:
        warmup_session = client.post("/v1/sessions").json()["session_id"]
        warmup_frame = encode_jpeg(dataset[0]["frame"])
        for sequence in range(args.warmup_frames):
            response = client.post(
                f"/v1/sessions/{warmup_session}/frames",
                files={"image": ("frame.jpg", warmup_frame, "image/jpeg")},
                data=temporal_form(
                    f"warmup:{warmup_session}",
                    sequence,
                    sequence / args.source_fps,
                    dataset[0]["frame"],
                ),
            )
            response.raise_for_status()
        client.delete(f"/v1/sessions/{warmup_session}")

        labels = application.state.detector.manifest.labels
        rates = [
            measure_rate(
                client,
                dataset,
                detector_fps,
                args.source_fps,
                args.display_fps,
                args.duration_seconds,
                len(labels),
            )
            for detector_fps in args.detector_fps
        ]

    return {
        "evidence_scope": "development diagnostic only; not deployment acceptance",
        "profile": machine_profile(args.device),
        "input": {
            "checkpoint": str(args.checkpoint),
            "checkpoint_manifest": str(args.checkpoint / "manifest.yaml"),
            "dataset": str(args.data_root),
            "session": args.session,
            "source_resolution": list(dataset[0]["frame"].shape[1::-1]),
            "assumed_source_fps": args.source_fps,
            "display_fps": args.display_fps,
            "duration_seconds": args.duration_seconds,
            "jpeg_quality": 90,
            "nms_iou": args.nms_iou,
        },
        "method": {
            "serving_path": "in-process FastAPI TestClient, sequential requests",
            "scheduler": "analytical replay of measured service times; no pending slot",
            "overlay_age": "capture-to-result measured; recorded-display hold age simulated",
            "quality": "measured on nominally selected synthetic frames, processed offline in order",
        },
        "rates": rates,
    }


def run_remote(args: argparse.Namespace) -> dict:
    import httpx

    dataset = SurgintDataset(args.data_root, f"eval/{args.session}", "detection-tracking")
    with httpx.Client(
        base_url=args.remote_url.rstrip("/"),
        follow_redirects=True,
        timeout=args.request_timeout,
    ) as client:
        ready = client.get("/health/ready")
        ready.raise_for_status()

        warmup_response = client.post("/v1/sessions")
        warmup_response.raise_for_status()
        warmup_session = warmup_response.json()["session_id"]
        warmup_frame = encode_jpeg(dataset[0]["frame"])
        try:
            for sequence in range(args.warmup_frames):
                response = client.post(
                    f"/v1/sessions/{warmup_session}/frames",
                    files={"image": ("frame.jpg", warmup_frame, "image/jpeg")},
                    data=temporal_form(
                        f"warmup:{warmup_session}",
                        sequence,
                        sequence / args.source_fps,
                        dataset[0]["frame"],
                    ),
                )
                response.raise_for_status()
                parse_server_timing(response.headers["server-timing"])
        finally:
            client.delete(f"/v1/sessions/{warmup_session}")

        rates = [
            measure_remote_rate(
                client,
                dataset,
                detector_fps,
                args.source_fps,
                args.display_fps,
                args.duration_seconds,
                len(dataset.mappings),
            )
            for detector_fps in args.detector_fps
        ]

    return {
        "evidence_scope": "bounded remote GPU measurement; not final deployment acceptance",
        "profile": {
            "remote_url": args.remote_url,
            "space_repo": args.space_repo,
            "space_revision": args.space_revision,
            "hardware": args.hardware,
            "source_commit": args.source_commit,
            "source_archive_sha256": args.source_archive_sha256,
            "base_image": args.base_image,
            "base_image_digest": args.base_image_digest,
            "model_source": args.model_source,
            "model_revision": args.model_revision,
            "model_weights_sha256": args.model_weights_sha256,
            "model_training_run": args.model_training_run,
            "model_dataset": args.model_dataset,
            "model_input": args.model_input,
        },
        "client": machine_profile("remote HTTPS client"),
        "input": {
            "dataset": str(args.data_root),
            "session": args.session,
            "source_resolution": list(dataset[0]["frame"].shape[1::-1]),
            "assumed_source_fps": args.source_fps,
            "display_fps": args.display_fps,
            "duration_seconds": args.duration_seconds,
            "jpeg_quality": 90,
            "nms_iou": 0.7,
        },
        "method": {
            "serving_path": "public HTTPS Space endpoint with sequential request-response",
            "scheduler": "actual wall-clock pacing with busy candidate frames not admitted",
            "overlay_age": "capture-to-result measured; held-overlay display clock replayed",
            "quality": "measured on the source frames actually admitted by the remote path",
        },
        "rates": rates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="?")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/synthetic/production_v5/dataset"),
    )
    parser.add_argument("--session", default="session_000")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--source-fps", type=float, default=20.0)
    parser.add_argument("--display-fps", type=float, default=20.0)
    parser.add_argument("--duration-seconds", type=float, default=5.0)
    parser.add_argument("--detector-fps", type=float, nargs="+", default=[5.0, 6.0, 10.0])
    parser.add_argument("--warmup-frames", type=int, default=2)
    parser.add_argument("--nms-iou", type=float, default=0.7)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--remote-url")
    parser.add_argument("--request-timeout", type=float, default=300.0)
    parser.add_argument("--space-repo")
    parser.add_argument("--space-revision")
    parser.add_argument("--hardware")
    parser.add_argument("--source-commit")
    parser.add_argument("--source-archive-sha256")
    parser.add_argument("--base-image")
    parser.add_argument("--base-image-digest")
    parser.add_argument("--model-source")
    parser.add_argument("--model-revision")
    parser.add_argument("--model-weights-sha256")
    parser.add_argument("--model-training-run")
    parser.add_argument("--model-dataset")
    parser.add_argument("--model-input", type=int, nargs=2)
    args = parser.parse_args()

    if args.remote_url:
        result = run_remote(args)
    elif args.checkpoint is not None:
        result = run(args)
    else:
        parser.error("checkpoint is required unless --remote-url is provided")
    serialized = json.dumps(result, indent=2)
    print(serialized)
    if args.output is not None:
        args.output.write_text(serialized + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
