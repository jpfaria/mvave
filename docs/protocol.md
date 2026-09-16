# M-VAVE MK-300 USB (SysEx) protocol

Measured on 2026-09-16 by spying on the M-EFCS editor (macOS, `com.digAmp.dgAmp` 3.7.1413,
Flutter + `flutter_midi_command`) with MIDI Monitor while it talked to an MK-300 on firmware
V73 over USB (CoreMIDI port `USB Composite Device`). Reproduced by the `mk300` package;
golden vectors in `tests/test_protocol.py`, raw captures in `docs/captures/` (`from-pedal.log.gz` = every frame the pedal sent during the session, `model_defaults.jsonl`, `knobs.json`).

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
| `0` | the **preset flash bank**: 160 × 448 bytes, byte offset = `slot × 448`. Read any slot without loading it (`read slot*448 / 448`, verified: slot 0 == the editor's factory record). Written by the editor's *Save to*: `cls 09`, `cmd 41` with the second 7-bit digit = `len/16` (`41 1C`), field `slot*448`, len 448, the 448-byte image as payload, then COMMIT, then a load of that slot | write to slot 159 and read-back verified live |
| `1` | the **edit buffer**: the 448-byte preset struct below | read 0/448 (whole preset), read 0x42/24 (one block's knobs), writes of 1–2 bytes at any offset |
| `2` | 86-byte **global / status** block, polled by the editor once per second (`read 0 len 86`): byte 0 = current preset index, 0x38 A/B Convert (0/1), 0x3C RCH (0 Nor, 1 Dry, 2 NoCAB), 0x3D USB Audio (0 ON, 1 OFF, 2 RESAMPLE, 3 DRY); the editor writes them with `write_u8` in space 2 | |
| `E` | **commands**: `write_u8(offset = preset index, 01)` loads that preset (0-based; editor label `[001]` = 0). The pedal acks, then the editor reads the edit buffer | |
| `F` | **commit**: `F0 00 32 09 41 00 00 00 02 00 00 00 00 0F 00 00 00 0B 00 F7` (cls 09, cmd 41, field 0, len 0, no payload) right after a bank write. The flash write takes a few seconds; commands sent meanwhile may cancel it — `mk300` waits until the slot reads back the new image before loading it | |

MIDI Monitor showed the editor's bank-write header as `09 41 1C 00 00 02 40 2C 04 00 38 00 00 4A …`
(one `00` fewer than the 4+4-digit header `mk300` sends); the pedal accepts the 4+4 form and the
slot changes, so that is what the library uses.

The pedal is also a 2-in/2-out 44.1 kHz USB audio interface (`USB-Audio`). With USB Audio =
RESAMPLE, USB playback goes through the effect chain and comes back on the USB input (a −20 dBFS
sine returned at −26 dBFS through JM-CL; DRY returns silence) — that is `mk300 reamp`.

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

| FX off | `F0 00 32 09 49 00 00 00 02 2C 00 00 00 11 00 00 00 00 7C 02 F7` |
| RCH = Dry (global) | `F0 00 32 09 49 00 00 00 02 3C 00 00 00 12 00 00 00 01 3A 02 F7` (space 2) |
| Save to [160] | 532-byte bank write (above) + COMMIT + load `F0 00 32 09 49 00 00 00 02 1F 01 00 00 1E 00 00 00 01 74 01 F7` |

## Knob values

int16 little-endian. 0–100 for most knobs; `Speed` ×10 (2.5 Hz = 25); delay `Time` in ms;
EQ bands and gate thresholds in dB (negative = two's complement, `Thd` −60 = `C4 FF`); `Sync` 0/1.
`DS`, `AMP` and `CAB` keep their knob values across a model change; the other blocks are reset to
the model's defaults (recorded in `mk300/catalog.json`).

## Not captured

Rename / chain reorder as the editor does them (`mk300` writes those bytes one by one with
`write_u8`, verified by read-back), the other global fields (Sync, Pedal State, toe switches, BT/USB
volumes — the editor's clicks were not observed writing them), the EQ / Looper / Drum pages, IR / AMP /
DS `.am3Data` uploads (Sounds and Import pages), footswitch assignments (bytes 0x14A… of the preset),
what the pedal broadcasts when a footswitch changes the preset (nothing beyond byte 0 of the polled
global block changing; `mk300 listen` polls it).

## Official MIDI CC map (from M-VAVE's "MK300 MIDI Control Mapping Table", firmware V73)

Channel 1 (`B0`). ≥ 64 = ON / execute, < 64 = OFF.

| CC | Function |
|---|---|
| 21 | Looper toggle (127: Record → Play → Overdub) / 0: Stop |
| 22 | Drum play/stop |
| 23 | Drum BPM follow |
| 32 | Looper stop |
| 33 | Looper undo / clear |
| 34 / 35 | AutoRecord one-shot / hold mode |
| 36 | Loop point toggle (127 tail / 0 head) |
| 37 / 39 | Drum sync mode 1 / 2 |
| 50–53 | FS1, FS2, CtrlA, CtrlB short press |
| 54–57 | FS1, FS2, CtrlA, CtrlB long press |
| 58 | RCH output mode 0 Nor / 1 Dry / 2 NoCAB |
| 59 | USB audio type 0 Nor / 1 No / 2 Resample / 3 Dry |
| 60 | BT & USB playback volume 0–100 |
| 61 | USB recording return volume 0–100 (50 = 0 dB) |
