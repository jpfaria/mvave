"""USB-MIDI transport for the MK-300 (mido / python-rtmidi, CoreMIDI port `USB Composite Device`)."""
from __future__ import annotations

import time

import mido

from . import protocol as p
from .preset import SIZE as PRESET_SIZE, Preset

PORT_HINT = "USB Composite Device"
_POLL_S = 0.005


def find_port(hint: str = PORT_HINT) -> str:
    names = [n for n in mido.get_input_names() if hint in n]
    if not names:
        raise RuntimeError(f"no MIDI port containing {hint!r}: {mido.get_input_names()}")
    return names[0]


class MK300:
    def __init__(self, port: str | None = None):
        port = port or find_port()
        self._in = mido.open_input(port)
        self._out = mido.open_output(port)
        self.port = port

    def close(self) -> None:
        self._in.close()
        self._out.close()

    def __enter__(self) -> "MK300":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- raw -------------------------------------------------------------------------
    def send(self, frame: bytes) -> None:
        self._out.send(mido.Message("sysex", data=frame[1:-1]))

    def receive(self, timeout: float = 1.0) -> bytes | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for m in self._in.iter_pending():
                if m.type == "sysex":
                    return bytes(m.bytes())
            time.sleep(_POLL_S)
        return None

    def drain(self) -> None:
        for _ in self._in.iter_pending():
            pass

    def write(self, frame: bytes, timeout: float = 1.5) -> None:
        """Send a write frame and wait for the pedal's ack (status polls from a running editor
        are skipped)."""
        self.drain()
        self.send(frame)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.receive(deadline - time.monotonic())
            if r is None:
                break
            if p.is_ack(r):
                return
        raise TimeoutError("no ack from the MK-300 (wrong checksum frames are silently dropped)")

    def read(self, field: int, length: int, space: int = p.SPACE_PRESET, timeout: float = 2.0) -> bytes:
        self.drain()
        self.send(p.read(field, length, space))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.receive(deadline - time.monotonic())
            if r is None:
                break
            try:
                f = p.parse(r)
            except ValueError:
                continue
            if f.cls == p.CLS_READ and f.field == field and f.space == space and len(f.payload) >= length:
                return f.payload[:length]
        raise TimeoutError(f"no reply to read {field:#x}/{length} in space {space}")

    # -- preset (edit buffer) ---------------------------------------------------------
    def read_preset(self) -> Preset:
        return Preset(self.read(0, PRESET_SIZE))

    def load_preset(self, index: int) -> None:
        self.write(p.load_preset(index))

    def set_u8(self, field: int, value: int, space: int = p.SPACE_PRESET) -> None:
        self.write(p.write_u8(field, value, space))

    def set_u16(self, field: int, value: int, space: int = p.SPACE_PRESET) -> None:
        self.write(p.write_u16(field, value, space))

    # -- global block (space 2) --------------------------------------------------------
    def read_global(self) -> bytes:
        return self.read(0, p.GLOBAL_SIZE, p.SPACE_STATUS)

    def current_preset_index(self) -> int:
        return self.read_global()[0]
