---
name: mk300
description: Use when the user wants to read or change anything on an M-VAVE MK-300 over USB without the M-EFCS editor — presets, blocks, models, knobs, on/off, chain order, name, save, copy, globals (RCH, USB audio), re-amp — e.g. "muda o gain do amp", "lista os presets da MK-300", "põe um delay analógico", "salva no 150", "que amps existem", or when an mk300 command times out. Not for building a song's tone from research: that is the tone-builder skill.
---

# mk300 — M-VAVE MK-300 over USB

CLI + Python package speaking the pedal's SysEx protocol. `reference.md` (next to this file) has
every command, the preset/global layouts and the full model catalog with knob names — read it
before composing commands. `mk300` with no arguments prints the command list.
Want the tone of a song or artist built as a preset? That is the **tone-builder** skill.

Setup: macOS, pedal on USB (port `USB Composite Device`). Not installed?
`pipx install git+https://github.com/jpfaria/mvave-mk-300` (or `pip install -e "${CLAUDE_PLUGIN_ROOT}"`).
The editor may stay open but does NOT show USB changes; its **Sync** button re-reads the buffer.
`mk300 show` is the source of truth.

## The pedal in one paragraph

Eleven fixed blocks in a fixed signal chain: `WAH FX GATE DS AMP CAB EQ MOD DLY REV VOL`. Every
block holds ONE model (`mk300 models BLOCK`) and up to 12 knobs (`mk300 params BLOCK MODEL`), and
is on or off. There are no scenes, no free slots: a second drive pedal goes in `FX` as a Boost, a
compressor in `FX` or `GATE`. `VOL` is the post volume (leave it on). Presets are `1..160` in
flash; `show`/`param`/`model`/`enable`/`rename` act on the **edit buffer** (RAM) — `save N NAME`
stores it, `load N` discards it.

## Numbering (most common mistake)

- Presets are **1-based** like the pedal's display: `[001]` = `1`. `DS/AMP/CAB` model names carry
  that same 1-based number (`53J900_CH1`), and `mk300 model AMP 53` accepts it. For the other
  blocks use the name (`model DLY Analog`) or the **0-based index** printed by `models`.
- Knobs: by name (`param AMP Gain 60`, `param CAB "Low Cut" 20`) or 0-based index.
- Units: knobs are 0-100 unless the catalog says otherwise; `Speed` knobs are x10 (2.5 Hz = 25),
  delay `Time` is ms (a note division only when `Sync` = 1 — set `Time` in ms from the BPM
  instead), EQ bands in dB (negative allowed), gate `Thd` in dB (negative).
- `DS`, `AMP`, `CAB` keep their knob values when you change the model; every other block resets
  to the model's defaults (`params` shows them).

## Recipes

**Change a knob and persist it**
```bash
mk300 show                                     # current preset, models, knob names/values
mk300 param AMP Gain 60 && mk300 param DLY Mix 20
mk300 save 5 "MY-CRUNCH" --overwrite            # slot 5 is named: --overwrite is required
mk300 read 5                                   # straight from flash, the proof it stuck
```

**Build a preset from scratch in a free slot**
```bash
mk300 presets                                  # free = "USER PRESET nnn"
mk300 load 150                                 # start from the empty template
mk300 model DS 2 && mk300 model AMP "J800 OD" && mk300 model CAB 10 && mk300 model DLY Analog && mk300 model REV Plate
mk300 param DS Gain 30 && mk300 param DLY Time 500 && mk300 param DLY Mix 20 && mk300 param REV Mix 15
mk300 enable DS on && mk300 enable AMP on && mk300 enable CAB on && mk300 enable DLY on && mk300 enable REV on
mk300 enable WAH off && mk300 enable FX off && mk300 enable GATE off && mk300 enable EQ off && mk300 enable MOD off
mk300 bpm 120 && mk300 save 150 "JCM-CRUNCH" && mk300 read 150
```

**Copy or move a preset**: `mk300 copy 3 150` (`--overwrite` to replace a named slot; move =
copy, then overwrite the source).

**Which model is based on a real unit**: `mk300 resolve AMP "Marshall JCM800"` — ties between
voicings (`_CL/_OD/_DS`) mean the query needs the channel word (`"JCM800 crunch OD"`).

**Globals** (RCH = right output mode, USB Audio mode, A/B convert):
```bash
mk300 global                                   # read the block first
mk300 global-set rch Dry                       # ONE write, then read again
```

**Re-amp a DI through the current preset**: `mk300 reamp di.wav wet.wav` (sets USB Audio =
RESAMPLE for the run and restores it; needs `pip install "mk300[reamp]"`).

**Follow the footswitches**: `mk300 listen 120` prints the preset index whenever it changes.

## Hard rules

- `save` and `copy` refuse a named slot without `--overwrite`; never pass `--overwrite` without
  the user's word for that slot. Factory presets are `1..152`-ish and user presets are wherever
  the user put them (`presets` shows names) — ask before overwriting anything that is not
  `USER PRESET nnn`.
- Globals: only the fields `mk300 global` lists, one write at a time. Never write other offsets
  of the global block.
- Never send raw frames or write offsets outside the preset struct; the library knows the
  checksum, a wrong frame is silently dropped and a wrong offset is a wrong preset.
- A timeout on any command means the pedal did not answer: repeat `mk300 show`; if it still
  times out, tell the user to power-cycle the pedal and re-check what was written.

## Not possible over USB (use the editor)

Importing IR/AMP/DS `.am3Data` files (Sounds and Import pages), the Looper/Drum/global EQ pages,
footswitch and toe-switch assignments, firmware updates.
