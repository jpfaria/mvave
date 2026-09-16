# M-VAVE MK-300 USB (SysEx) protocol

Measured on 2026-09-16 by spying on the M-EFCS editor (macOS, `com.digAmp.dgAmp` 3.7.1413,
Flutter + `flutter_midi_command`) with MIDI Monitor while it talked to an MK-300 on firmware
V73 over USB (CoreMIDI port `USB Composite Device`). Reproduced by the `mk300` package;
golden vectors in `tests/test_protocol.py`, raw captures in `docs/captures/`.

## Frame

```
F0 00 32 | CLS | CMD lo .. hi (4) | 02 | FIELD (4) | SUB (4) | packed(payload + ck8) | F7
```

| Part | Meaning |
|---|---|
| `00 32` | manufacturer id |
| `CLS` | `09` write (host→pedal with data), `0D` read query and every data reply, `01` ack |
| `CMD` | `41` read, `49` write 1 byte, `51` write 2 bytes; replies echo `41` (dump), `71 05` (status), `01 02` (block read). 4 bytes, 7-bit little-endian |
| `FIELD` | **byte offset** inside the addressed memory space, 7-bit LE u32 |
| `SUB` | `(len << 4) | space`, 7-bit LE u32. `len` = size of the addressed object in bytes |
| packed | the 8-bit payload followed by one checksum byte, packed **LSB-first, 7 bits per SysEx byte** (bit *i* of the byte stream = bit *i* of the packed stream) |

The 14 header bytes are plain (not packed). `ck8 = 0xFB − (Σpayload + Σ FIELD bytes + Σ bytes
of u32 (len << 8 | space << 4))` mod 256; CLS and CMD are not covered. The pedal **verifies
it**: a frame with a wrong checksum gets no reply at all (tested with the status poll).

Ack for every write: `F0 00 32 01 08 00 00 00 00 7F 01 F7`.

## Memory spaces

| space | content | seen |
|---|---|---|
| `1` | the **edit buffer**: the 448-byte preset struct below | read 0/448 (whole preset), read 0x42/24 (one block's knobs), writes of 1–2 bytes at any offset |
| `2` | 86-byte **status** block, polled by the editor once per second (`read 0 len 86`); byte 0 = current preset index | |
| `E` | **commands**: `write_u8(offset = preset index, 01)` loads that preset (0-based; editor label `[001]` = 0). The pedal acks, then the editor reads the edit buffer | |

## Preset struct (448 bytes, space 1; identical to the records of the editor's factory bank `mk300_am4_preset.bin` = 160 × 448 + "PATCHEND")

| Offset | Size | Content |
|---|---|---|
| 0x00 | 20 | name, NUL-padded |
| 0x14 | 4 | `FF 90 1E 00` in every factory preset (unknown) |
| 0x18 | u16 | Preset Vol (0–100) |
| 0x1A | u16 | BPM |
| 0x1C | u16 | Pan: `C` = 0, `R17` = 17 (left side: not captured yet) |
| 0x20 | 11 | chain order: block ids in signal order (factory: `00 01 02 03 04 05 06 07 09 08 0A`) |
| 0x2B | 11 | block on/off, indexed by block id |
| 0x36 | 11 | model index per block, indexed by block id (+1 pad byte) |
| 0x42 | 11 × 24 | knobs per block, indexed by block id: 12 × u16 each |
| 0x14A | … | footswitch / control assignments (pairs like `09 0B`, `08 0A`, `0D 12`), not decoded |
| 0x1BF | 1 | `45` in every factory preset |

Block ids: 0 WAH, 1 FX, 2 GATE, 3 DS, 4 AMP, 5 CAB, 6 EQ, 7 MOD, 8 DLY, 9 REV, 10 VOL.
Knob *k* of block *b* is at `0x42 + 24·b + 2·k`; the editor writes it with `write_u16`.
Model of block *b* is at `0x36 + b` (`write_u8`; the pedal then resets that block's knobs to the
model defaults and the editor re-reads `0x42 + 24·b`, 24 bytes). On/off of block *b* is at
`0x2B + b` (`write_u8` 0/1).

## Captured editor messages

| Action | Frame |
|---|---|
| status poll | `F0 00 32 0D 41 00 00 00 02 00 00 00 00 62 0A 00 00 05 01 F7` |
| read edit buffer | `F0 00 32 0D 41 00 00 00 02 00 00 00 00 01 38 00 00 2A 00 F7` → 532-byte reply, 448-byte payload |
| read WAH knobs | `F0 00 32 0D 41 00 00 00 02 42 00 00 00 01 03 00 00 11 01 F7` → 47-byte reply, 24-byte payload |
| Preset Vol = 60 | `F0 00 32 09 51 00 00 00 02 18 00 00 00 21 00 00 00 3C 00 54 04 F7` |
| BPM = 133 | `F0 00 32 09 51 00 00 00 02 1A 00 00 00 21 00 00 00 05 01 28 02 F7` |
| Pan = R17 | `F0 00 32 09 51 00 00 00 02 1C 00 00 00 21 00 00 00 11 00 70 05 F7` |
| WAH knob 0 = 70 | `F0 00 32 09 51 00 00 00 02 42 00 00 00 21 00 00 00 46 00 04 03 F7` |
| WAH model = 1 (Funk-Wah) | `F0 00 32 09 49 00 00 00 02 36 00 00 00 11 00 00 00 01 66 02 F7` |
| FX off | `F0 00 32 09 49 00 00 00 02 2C 00 00 00 11 00 00 00 00 7C 02 F7` |
| load preset [003] | `F0 00 32 09 49 00 00 00 02 02 00 00 00 1E 00 00 00 01 2E 00 F7` (sent twice by the editor) |

## Not captured yet

Save to flash, rename, chain reorder, global settings, EQ / looper / drum pages, IR / AMP / DS
uploads, footswitch assignments, what the pedal broadcasts when a footswitch changes the preset.
