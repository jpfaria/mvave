"""Mackie Control: the language the SMC-Mixer speaks in DAW mode.

Nothing here is M-EFCS -- this is the other protocol M-VAVE ships. It is plain
MIDI: faders are 14-bit pitch bend, encoders are relative CCs, buttons are
notes, and every LED is lit by sending the same note back. Measured on an
SMC-Mixer on 2026-09-21 (see docs/smc-mixer.md).
"""
from __future__ import annotations

from dataclasses import dataclass

# Button note = BASE + channel (channel is 0-based).
REC, SOLO, MUTE, SELECT = 0x00, 0x08, 0x10, 0x18
BANK_LEFT, BANK_RIGHT = 0x2E, 0x2F
REWIND, FORWARD, STOP, PLAY, RECORD = 0x5B, 0x5C, 0x5D, 0x5E, 0x5F
ARROW_LEFT, ARROW_RIGHT = 0x62, 0x63

VPOT = 0x10             # encoder n = CC VPOT + n
FADER_MAX = 16383

ON, OFF = 127, 0


@dataclass(frozen=True)
class Fader:
    channel: int        # 0-based
    value: float        # 0..1


@dataclass(frozen=True)
class Encoder:
    channel: int        # 0-based
    delta: int          # +1 / -1 per detent


@dataclass(frozen=True)
class Button:
    note: int
    pressed: bool

    @property
    def channel(self) -> int | None:
        """Channel of a per-channel button (REC/SOLO/MUTE/SELECT), else None."""
        for base in (REC, SOLO, MUTE, SELECT):
            if base <= self.note < base + 8:
                return self.note - base
        return None

    @property
    def kind(self) -> str:
        for base, name in ((REC, "rec"), (SOLO, "solo"),
                           (MUTE, "mute"), (SELECT, "select")):
            if base <= self.note < base + 8:
                return name
        return {BANK_LEFT: "bank_left", BANK_RIGHT: "bank_right",
                ARROW_LEFT: "arrow_left", ARROW_RIGHT: "arrow_right",
                REWIND: "rewind", FORWARD: "forward", STOP: "stop",
                PLAY: "play", RECORD: "record"}.get(self.note, "unknown")


def decode(msg) -> Fader | Encoder | Button | None:
    """A mido message -> what the surface did, or None for anything else."""
    if msg.type == "pitchwheel":
        # mido centres pitch bend on 0 (-8192..8191); the surface sends it as
        # an unsigned 14-bit position, so shift it back.
        return Fader(msg.channel, (msg.pitch + 8192) / FADER_MAX)
    if msg.type == "control_change" and VPOT <= msg.control < VPOT + 8:
        # relative: 0x01..0x3F turns right, 0x41..0x7F turns left
        delta = msg.value if msg.value < 0x40 else -(msg.value - 0x40)
        return Encoder(msg.control - VPOT, delta)
    if msg.type in ("note_on", "note_off"):
        return Button(msg.note, msg.type == "note_on" and msg.velocity > 0)
    return None


def led(note: int, on: bool) -> dict:
    """Message kwargs that light (or clear) a button's LED."""
    return {"type": "note_on", "note": note, "velocity": ON if on else OFF}


def fader_position(channel: int, value: float) -> dict:
    """Message kwargs that tell the surface where a fader *should* be.

    The fader has no motor: the surface blinks that channel's LED until the
    physical position matches this value.
    """
    bruto = max(0, min(FADER_MAX, round(value * FADER_MAX)))
    return {"type": "pitchwheel", "channel": channel, "pitch": bruto - 8192}
