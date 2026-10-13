import math

import pytest

from surgint.runtime.temporal import FrameIdentity, MetadataOrigin, ResultTiming


def test_frame_identity_retains_valid_source_metadata():
    identity = FrameIdentity(
        source_id="camera:alpha-1",
        sequence=7,
        captured_at=12.5,
        source_width=1280,
        source_height=720,
    )

    assert identity.source_size == (1280, 720)
    assert identity.origin is MetadataOrigin.CLIENT


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", "contains a space"),
        ("sequence", -1),
        ("captured_at", -0.1),
        ("captured_at", math.nan),
        ("captured_at", math.inf),
        ("source_width", 0),
        ("source_height", -1),
    ],
)
def test_frame_identity_rejects_invalid_metadata(field, value):
    values = {
        "source_id": "camera:alpha",
        "sequence": 0,
        "captured_at": 0.0,
        "source_width": 1280,
        "source_height": 720,
    }
    values[field] = value

    with pytest.raises(ValueError):
        FrameIdentity(**values)


def test_result_timing_requires_monotonic_server_boundaries():
    timing = ResultTiming(10.0, 10.1, 10.2, 10.3)
    assert timing.processing_completed_at == 10.2

    with pytest.raises(ValueError, match="monotonic"):
        ResultTiming(10.0, 10.2, 10.1, 10.3)
