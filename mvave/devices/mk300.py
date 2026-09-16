"""M-VAVE MK-300 profile: the 448-byte preset struct (edit buffer, memory space 1), the global
block fields and the catalog file. See docs/protocol.md."""
from __future__ import annotations

from dataclasses import dataclass, field

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


GLOBAL_FIELDS = {  # offset in space 2 -> (name, values)   (see docs/protocol.md)
    0x38: ("ab-convert", ["OFF", "ON"]),
    0x3C: ("rch", ["Nor", "Dry", "NoCAB"]),
    0x3D: ("usb-audio", ["ON", "OFF", "RESAMPLE", "DRY"]),
}


@dataclass(frozen=True)
class Profile:
    name: str = "mk300"
    port_hint: str = "USB Composite Device"      # CoreMIDI port name fragment
    audio_device: str = "USB-Audio"              # CoreAudio device name (2 in / 2 out, 44.1 kHz)
    preset_size: int = SIZE
    slots: int = 160
    global_size: int = 86
    catalog_file: str = "mk300_catalog.json"
    blocks: tuple = tuple(BLOCKS)
    global_fields: dict = field(default_factory=lambda: dict(GLOBAL_FIELDS))
    usb_audio_field: int = 0x3D
    usb_audio_resample: int = 2
    preset_cls: type = Preset

    def preset(self, raw: bytes) -> Preset:
        return self.preset_cls(raw)


PROFILE = Profile()
