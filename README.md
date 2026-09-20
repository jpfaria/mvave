# mvave

Control **M-VAVE pedals** over USB without the M-EFCS editor: the reverse-engineered SysEx protocol
of the editor (shared by every pedal it supports), a Python library, a CLI, and one **device
profile** per pedal — today the **MK-300** (firmware V73, September 2026) with a catalog of all
359 built-in models and their knobs. `mvave --device mk300 …`; `mk300` is the default.

```bash
pip install git+https://github.com/jpfaria/mvave   # or: pip install -e .
mvave presets                       # the 160 stored presets (* = current)
mvave show                          # the edit buffer: name, chain, models, knobs, on/off
mvave load 3                        # load preset [003] (1..160) and show it
mvave read 150                      # a stored preset straight from flash, without loading it
mvave model AMP 53                  # 53J900_CH1 in the AMP block (knobs reset to the model defaults)
mvave model DLY "Analog Stereo"
mvave param AMP Gain 60             # knob by name or 0-based index
mvave enable DLY off                # block on/off
mvave volume 70 && mvave bpm 120 && mvave pan -10
mvave rename MY-CRUNCH && mvave save 150 MY-CRUNCH   # store the edit buffer (refuses a named slot without --overwrite)
mvave copy 3 151                    # copy a stored preset to another slot
mvave chain GATE WAH FX DS AMP CAB EQ MOD DLY REV VOL   # signal order
mvave reamp di.wav wet.wav          # play a DI through the current preset over USB audio, record the result
mvave models MOD                    # catalog: models of a block with their knobs
mvave params FX Whammy              # knobs + defaults of one model
mvave resolve AMP "Marshall JCM800" # which models are based on a real-world unit
mvave global && mvave global-set rch Dry
mvave listen 120                    # print the preset index when a footswitch changes it
mvave                               # every command
```

`python3 -m mvave` works without the console script.

## Covered

Presets (list, read from flash, load, save, copy, rename), the edit buffer (name, volume, BPM,
pan, chain order, block on/off, model per block, 12 knobs per block), the global block (read; RCH,
USB Audio, A/B convert writes), the catalog of all 359 models with knob names and the defaults the
pedal loads (`docs/catalog.md`, with what each block does and what the model names point at),
catalog lookup by real-world gear name (`resolve`), re-amping over USB audio (`reamp`, extra
`mk300[reamp]`), following footswitch preset changes (`listen`). Byte-level details:
[docs/protocol.md](docs/protocol.md).

## Not covered

IR / AMP / DS model uploads (`.nam` and `.am4Data`; this MK-300 is AM4 and imports NAM) (the Sounds and Import pages), the Looper / Drum / global EQ
pages, footswitch and toe-switch assignments, the other global fields. The editor was only
observed for the messages listed in `docs/protocol.md`; the library does not guess.

## Rules that keep the pedal predictable

- Every frame carries a checksum the pedal verifies: a wrong one is silently dropped (no
  reply). The library computes it; if a command times out, nothing happened.
- Writes go to the **edit buffer** (RAM); `mvave load N` discards them. `save` / `copy` write
  flash and refuse a slot that already has a name unless `--overwrite` is given. After a flash
  write the pedal is busy for a few seconds; the library waits for the slot to read back.
- Global settings: write only the fields listed in `mvave global`, one at a time.
- The editor does not follow changes made over USB; its **Sync** button re-reads the buffer.

## Requirements

macOS (CoreMIDI through `python-rtmidi`), Python ≥ 3.11, the pedal on USB (port `USB Composite
Device`). The editor can stay open. [tone-analyzer](https://github.com/jpfaria/tone-analyzer)
is installed as a dependency (the tone-builder skill measures with it).

## Claude Code plugin

This repo is also a plugin marketplace with two skills: `mvave` (configure the pedal: the CLI
and the rules above) and `tone-builder` (build the tone of a song as a preset from cited gear
research).

```bash
claude plugin marketplace add jpfaria/mvave
claude plugin install mvave@mvave
```

## Development

```bash
pip install -e ".[dev]" && pytest -q      # golden vectors captured from the editor (docs/captures)
python3 tools/build_reference.py           # regenerate skills/mvave/reference.md and docs/catalog.md
```

## Adding another M-VAVE pedal

The protocol (`mvave/protocol.py`) is the editor's and does not change. A new pedal is a new module
in `mvave/devices/` (preset struct offsets, global fields, a `*_catalog.json`) plus its entry in
`PROFILES`; capture the editor's traffic for that pedal the way `docs/protocol.md` describes.
