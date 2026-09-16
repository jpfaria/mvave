"""The 448-byte preset struct (edit buffer, memory space 1). See docs/protocol.md."""
from __future__ import annotations

from dataclasses import dataclass

SIZE = 448
BLOCKS = ["WAH", "FX", "GATE", "DS", "AMP", "CAB", "EQ", "MOD", "DLY", "REV", "VOL"]
BLOCK_ID = {name: i for i, name in enumerate(BLOCKS)}

OFF_NAME = 0x00        # 20 bytes, NUL padded
OFF_VOL = 0x18         # u16
OFF_BPM = 0x1A         # u16
OFF_PAN = 0x1C         # i16, C = 0, R17 = 17
OFF_CHAIN = 0x20       # 11 block ids in signal order
OFF_ENABLED = 0x2B     # 11 bytes indexed by block id
OFF_MODEL = 0x36       # 11 bytes indexed by block id
OFF_KNOBS = 0x42       # 11 x 12 x i16 indexed by block id
KNOBS_PER_BLOCK = 12
KNOB_BYTES = 2 * KNOBS_PER_BLOCK


def knob_offset(block: int, knob: int) -> int:
    return OFF_KNOBS + KNOB_BYTES * block + 2 * knob


def model_offset(block: int) -> int:
    return OFF_MODEL + block


def enabled_offset(block: int) -> int:
    return OFF_ENABLED + block


def _i16(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off + 2], "little", signed=True)


@dataclass(frozen=True)
class Preset:
    raw: bytes

    def __post_init__(self):
        if len(self.raw) != SIZE:
            raise ValueError(f"preset image must be {SIZE} bytes, got {len(self.raw)}")

    @property
    def name(self) -> str:
        return self.raw[OFF_NAME:OFF_NAME + 20].split(b"\0")[0].decode("latin-1")

    @property
    def volume(self) -> int:
        return _i16(self.raw, OFF_VOL)

    @property
    def bpm(self) -> int:
        return _i16(self.raw, OFF_BPM)

    @property
    def pan(self) -> int:
        return _i16(self.raw, OFF_PAN)

    @property
    def chain(self) -> list[int]:
        return list(self.raw[OFF_CHAIN:OFF_CHAIN + 11])

    def enabled(self, block: int) -> bool:
        return bool(self.raw[enabled_offset(block)])

    def model(self, block: int) -> int:
        return self.raw[model_offset(block)]

    def knobs(self, block: int) -> list[int]:
        return [_i16(self.raw, knob_offset(block, k)) for k in range(KNOBS_PER_BLOCK)]

    def knob(self, block: int, knob: int) -> int:
        return _i16(self.raw, knob_offset(block, knob))


def parse_bank(data: bytes) -> list[Preset]:
    """Split a bank file (the editor's mk300_am4_preset.bin: 160 x 448 + 'PATCHEND')."""
    n = len(data) // SIZE
    return [Preset(data[i * SIZE:(i + 1) * SIZE]) for i in range(n)]
