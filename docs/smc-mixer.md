# M-VAVE SMC-Mixer

Control surface, not a pedal: 8 faders, 8 endless encoders, 43 buttons, USB-C
and BLE, 780 mAh battery. It does **not** speak M-EFCS — in DAW mode it speaks
**Mackie Control**, which is `mvave/mackie.py`.

Everything below was measured on 2026-09-21 with the device on Bluetooth.

## Ports

CoreMIDI shows `SMC-Mixer-Master` (used here) and a `SMC-Mixer-Private` twin.
Over USB-C it is class-compliant and charges at the same time; the manual and
the Mixxx docs both recommend the cable for live use.

## Messages

| Control | Message |
|---|---|
| Fader n | Pitch Bend on channel n — unsigned 14-bit position |
| Encoder n | CC `0x10`+n−1, **relative**: `01` = +1, `41` = −1 |
| Mute / Solo / Rec / Select of channel n | Note On `0x10` / `0x08` / `0x00` / `0x18` + n−1 |
| Channel ◀ / ▶ | Note `2E` / `2F` |
| Arrows ◀ / ▶ | Note `62` / `63` |
| Rewind / Forward / Stop / Play / Record | Note `5B` / `5C` / `5D` / `5E` / `5F` |

Every LED is lit by sending the same note back with velocity 127 (0 clears it).
Sending a Pitch Bend makes that channel's LED **blink until the physical fader
matches** — the fader has no motor.

## What it cannot do

- **No internal preset.** Shift + the two bottom-right buttons switch DAW mode ↔
  User/CC mode; the lit button under Shift is the current mode. Channel ◀/▶ only
  pages the host's 8-track window.
- **No position report.** The Mackie Device Query (`F0 00 00 66 14 00 F7`) gets
  no fader positions back, so a host cannot ask where the faders are. That is
  why `mvave.bridge` uses soft takeover: a fader only starts writing once it
  crosses the current value, otherwise touching it would jump the volume.
- Shift blinking on its own is the **low-battery** warning (manual).
- The configuration app (MidiSuite) is Windows-only, and as of 21/09 the
  official download page lists only NAM A2, MK-300 and TANK-PRO — nothing for
  the SMC-Mixer.
