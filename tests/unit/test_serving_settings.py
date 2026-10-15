from pathlib import Path

from services.api.settings import DEFAULT_CHECKPOINT, DEFAULT_DEVICE, ServingSettings


def test_runtime_defaults_use_downloaded_model_on_cuda(monkeypatch) -> None:
    monkeypatch.delenv("CHECKPOINT", raising=False)
    monkeypatch.delenv("DEVICE", raising=False)
    monkeypatch.setenv("SURGINT_CHECKPOINT", "/legacy/model")
    monkeypatch.setenv("SURGINT_DEVICE", "cpu")

    settings = ServingSettings.from_environment()

    assert settings.checkpoint == DEFAULT_CHECKPOINT
    assert settings.checkpoint == Path("models/surgint-instruments-rt-detr")
    assert settings.device == DEFAULT_DEVICE == "cuda"


def test_runtime_defaults_accept_explicit_overrides(monkeypatch) -> None:
    monkeypatch.setenv("CHECKPOINT", "/models/custom")
    monkeypatch.setenv("DEVICE", "cuda:1")

    settings = ServingSettings.from_environment()

    assert settings.checkpoint == Path("/models/custom")
    assert settings.device == "cuda:1"
