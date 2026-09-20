---
name: mvave
description: Use when the user wants to read or change anything on an M-VAVE pedal (MK-300 mapped; same M-EFCS protocol for the others) over USB without the M-EFCS editor — presets, blocks, models, knobs, on/off, chain order, name, save, copy, globals (RCH, USB audio), re-amp — e.g. "muda o gain do amp", "lista os presets da MK-300", "põe um delay analógico", "salva no 150", "que amps existem", or when an mvave command times out. Not for building a song's tone from research: that is the tone-builder skill.
---

# mvave — M-VAVE pedals over USB

CLI + Python package speaking the M-EFCS editor's SysEx protocol; `--device` picks the pedal
profile (only `mk300` is mapped today, and it is the default, so `mvave show` = `mvave --device mk300 show`). `reference.md` (next to this file) has
every command, the preset/global layouts and the full model catalog with knob names — read it
before composing commands. `mvave` with no arguments prints the command list.
Want the tone of a song or artist built as a preset? That is the **tone-builder** skill.

Setup: macOS, pedal on USB (MK-300 port `USB Composite Device`). Not installed?
`pip install git+https://github.com/jpfaria/mvave` (or `pip install -e "${CLAUDE_PLUGIN_ROOT}"`).
The editor may stay open but does NOT show USB changes; its **Sync** button re-reads the buffer.
`mvave show` is the source of truth.

## The pedal in one paragraph

Eleven fixed blocks in a fixed signal chain: `WAH FX GATE DS AMP CAB EQ MOD DLY REV VOL`. Every
block holds ONE model (`mvave models BLOCK`) and up to 12 knobs (`mvave params BLOCK MODEL`), and
is on or off. There are no scenes, no free slots: a second drive pedal goes in `FX` as a Boost, a
compressor in `FX` or `GATE`. `VOL` is the post volume (leave it on). Presets are `1..160` in
flash; `show`/`param`/`model`/`enable`/`rename` act on the **edit buffer** (RAM) — `save N NAME`
stores it, `load N` discards it.

## Numbering (most common mistake)

- Presets are **1-based** like the pedal's display: `[001]` = `1`. `DS/AMP/CAB` model names carry
  that same 1-based number (`53J900_CH1`), and `mvave model AMP 53` accepts it. For the other
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
mvave show                                     # current preset, models, knob names/values
mvave param AMP Gain 60 && mvave param DLY Mix 20
mvave save 5 "MY-CRUNCH" --overwrite            # slot 5 is named: --overwrite is required
mvave read 5                                   # straight from flash, the proof it stuck
```

**Build a preset from scratch in a free slot**
```bash
mvave presets                                  # free = "USER PRESET nnn"
mvave load 150                                 # start from the empty template
mvave model DS 2 && mvave model AMP "J800 OD" && mvave model CAB 10 && mvave model DLY Analog && mvave model REV Plate
mvave param DS Gain 30 && mvave param DLY Time 500 && mvave param DLY Mix 20 && mvave param REV Mix 15
mvave enable DS on && mvave enable AMP on && mvave enable CAB on && mvave enable DLY on && mvave enable REV on
mvave enable WAH off && mvave enable FX off && mvave enable GATE off && mvave enable EQ off && mvave enable MOD off
mvave bpm 120 && mvave save 150 "JCM-CRUNCH" && mvave read 150
```

**Copy or move a preset**: `mvave copy 3 150` (`--overwrite` to replace a named slot; move =
copy, then overwrite the source).

**Which model is based on a real unit**: `mvave resolve AMP "Marshall JCM800"` — ties between
voicings (`_CL/_OD/_DS`) mean the query needs the channel word (`"JCM800 crunch OD"`).

**Globals** (RCH = right output mode, USB Audio mode, A/B convert):
```bash
mvave global                                   # read the block first
mvave global-set rch Dry                       # ONE write, then read again
```

**Re-amp a DI through the current preset**: `mvave reamp di.wav wet.wav` (sets USB Audio =
RESAMPLE for the run and restores it; needs `pip install "mvave[reamp]"`). USB Audio is
**borrowed state**: RESAMPLE makes the pedal ignore the guitar input and process USB playback
instead, so it must never be left set after the run — `reamp` guarantees the restore (normal
exit, exception, or Ctrl-C/kill) via `mvave.usb_audio.borrowed_usb_audio`, the only code path
allowed to write that field. If a run is interrupted in a way that skips even that (killed
process), or you're not sure: `mvave doctor` reads the globals and reports it (exit 1) with the
fix (`mvave global-set usb-audio 0`).

**Follow the footswitches**: `mvave listen 120` prints the preset index whenever it changes.

**Sanity-check the pedal before playing**: `mvave doctor` — exit 0 and "ok" means nothing is
left in a state (like USB Audio != ON) that would make the pedal silent for normal guitar
playing; exit 1 prints what's wrong and the exact command to fix it.

## Hard rules

- `save` and `copy` refuse a named slot without `--overwrite`; never pass `--overwrite` without
  the user's word for that slot. Factory presets are `1..152`-ish and user presets are wherever
  the user put them (`presets` shows names) — ask before overwriting anything that is not
  `USER PRESET nnn`.
- Globals: only the fields `mvave global` lists, one write at a time. Never write other offsets
  of the global block.
- Never send raw frames or write offsets outside the preset struct; the library knows the
  checksum, a wrong frame is silently dropped and a wrong offset is a wrong preset.
- A timeout on any command means the pedal did not answer: repeat `mvave show`; if it still
  times out, tell the user to power-cycle the pedal and re-check what was written.
- If you're adding new code that needs USB Audio in RESAMPLE (or any mode other than ON) even
  briefly, do it through `mvave.usb_audio.borrowed_usb_audio(device)` — never `device.set_u8`
  the field directly. That's what makes the restore unconditional (success, exception, signal);
  a direct write does not.

## Not possible over USB (use the editor)

Importing IR/AMP/DS models (Sounds and Import pages), the Looper/Drum/global EQ pages,
footswitch and toe-switch assignments, firmware updates.

**The MK-300 is AM4 and imports `.nam` (NAM) files** as AMP/DS models, besides `.am4Data`.
`.am3Data` is the older generation's format — never tell the user the pedal "only takes AM3".
