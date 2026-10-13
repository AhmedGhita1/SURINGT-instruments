import re
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Integral, Real


SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class TemporalContractError(ValueError):
    """Base error for invalid source-time contracts."""


class SourceIdentityError(TemporalContractError):
    """A frame belongs to a different source than the active sequence."""


class FrameOrderError(TemporalContractError):
    """A frame does not advance sequence and source time."""


class FrameDimensionError(TemporalContractError):
    """Declared source dimensions do not match the decoded frame."""


class MetadataOrigin(str, Enum):
    CLIENT = "client"
    SERVER_GENERATED_LEGACY = "server-generated-legacy"


@dataclass(frozen=True)
class FrameIdentity:
    """Identity and source-clock position of one selected frame."""

    source_id: str
    sequence: int
    captured_at: float
    source_width: int
    source_height: int
    origin: MetadataOrigin = MetadataOrigin.CLIENT

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not SOURCE_ID.fullmatch(self.source_id):
            raise TemporalContractError(
                "source_id must be 1 to 128 ASCII letters, digits, dots, colons, underscores, "
                "or hyphens"
            )
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, Integral):
            raise TemporalContractError("sequence must be a non-negative integer")
        if self.sequence < 0:
            raise TemporalContractError("sequence must be a non-negative integer")
        if isinstance(self.captured_at, bool) or not isinstance(self.captured_at, Real):
            raise TemporalContractError("captured_at must be a finite non-negative number")
        if not isfinite(float(self.captured_at)) or self.captured_at < 0.0:
            raise TemporalContractError("captured_at must be a finite non-negative number")
        for name, value in (
            ("source_width", self.source_width),
            ("source_height", self.source_height),
        ):
            if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
                raise TemporalContractError(f"{name} must be a positive integer")
        if not isinstance(self.origin, MetadataOrigin):
            raise TemporalContractError("origin must identify client or server-generated metadata")

        object.__setattr__(self, "sequence", int(self.sequence))
        object.__setattr__(self, "captured_at", float(self.captured_at))
        object.__setattr__(self, "source_width", int(self.source_width))
        object.__setattr__(self, "source_height", int(self.source_height))

    @property
    def source_size(self) -> tuple[int, int]:
        return self.source_width, self.source_height


@dataclass(frozen=True)
class ResultTiming:
    """Server-monotonic boundaries for one frame result."""

    received_at: float
    processing_started_at: float
    processing_completed_at: float
    result_created_at: float

    def __post_init__(self) -> None:
        values = (
            self.received_at,
            self.processing_started_at,
            self.processing_completed_at,
            self.result_created_at,
        )
        if any(not isfinite(value) or value < 0.0 for value in values):
            raise TemporalContractError("result timing values must be finite and non-negative")
        if any(later < earlier for earlier, later in zip(values, values[1:])):
            raise TemporalContractError("result timing values must be monotonic")
