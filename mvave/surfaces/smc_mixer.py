"""M-VAVE SMC-Mixer: 8 faders, 8 endless encoders, 43 buttons, USB-C + BLE.

In DAW mode it speaks Mackie Control (`mvave.mackie`); User/CC mode is set on
the device itself with Shift + the two bottom-right buttons. It has no motor
and no internal preset: what a fader "is" comes from whoever it is bridged to.

Measured 2026-09-21: over Bluetooth CoreMIDI shows `SMC-Mixer-Master` (and a
`-Private` twin); the Mackie Device Query gets no position report back, so a
host cannot ask where the faders are -- hence soft takeover in the bridge.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Surface:
    name: str
    port_hint: str
    faders: int
    encoders: int
    channel_buttons: tuple[str, ...]
    notes: str = ""


SURFACE = Surface(
    name="SMC-Mixer",
    port_hint="SMC-Mixer-Master",
    faders=8,
    encoders=8,
    channel_buttons=("mute", "solo", "rec", "select"),
    notes="DAW mode = Mackie Control. Shift + bottom-right pair switches mode; "
          "the lit button under Shift is the mode in use. Shift blinking on its "
          "own is the low-battery warning.",
)
