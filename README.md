# mvave-mk-300

Control an **M-VAVE MK-300** over USB without the M-EFCS editor: the reverse-engineered SysEx
protocol (September 2026, firmware V73) plus a Python library, a CLI and a catalog of all 359
built-in models with their knobs.

```bash
pipx install git+https://github.com/jpfaria/mvave-mk-300   # or: pip install -e .
mk300 presets                       # the 160 stored presets (* = current)
mk300 show                          # the edit buffer: name, chain, models, knobs, on/off
mk300 load 3                        # load preset [003] (1..160) and show it
mk300 read 150                      # a stored preset straight from flash, without loading it
mk300 model AMP 53                  # 53J900_CH1 in the AMP block (knobs reset to the model defaults)
mk300 model DLY "Analog Stereo"
mk300 param AMP Gain 60             # knob by name or 0-based index
mk300 enable DLY off                # block on/off
mk300 volume 70 && mk300 bpm 120 && mk300 pan -10
mk300 rename MY-CRUNCH && mk300 save 150 MY-CRUNCH   # store the edit buffer (refuses a named slot without --overwrite)
mk300 copy 3 151                    # copy a stored preset to another slot
mk300 chain GATE WAH FX DS AMP CAB EQ MOD DLY REV VOL   # signal order
mk300 reamp di.wav wet.wav          # play a DI through the current preset over USB audio, record the result
mk300 models MOD                    # catalog: models of a block with their knobs
mk300 params FX Whammy              # knobs + defaults of one model
mk300 resolve AMP "Marshall JCM800" # which models are based on a real-world unit
mk300 global && mk300 global-set rch Dry
mk300 listen 120                    # print the preset index when a footswitch changes it
mk300                               # every command
```

`python3 -m mk300` works without the console script.

## Covered

Presets (list, read from flash, load, save, copy, rename), the edit buffer (name, volume, BPM,
pan, chain order, block on/off, model per block, 12 knobs per block), the global block (read; RCH,
USB Audio, A/B convert writes), the catalog of all 359 models with knob names and the defaults the
pedal loads (`docs/catalog.md`, with what each block does and what the model names point at),
catalog lookup by real-world gear name (`resolve`), re-amping over USB audio (`reamp`, extra
`mk300[reamp]`), following footswitch preset changes (`listen`). Byte-level details:
[docs/protocol.md](docs/protocol.md).

## Not covered

IR / AMP / DS `.am3Data` uploads (the Sounds and Import pages), the Looper / Drum / global EQ
pages, footswitch and toe-switch assignments, the other global fields. The editor was only
observed for the messages listed in `docs/protocol.md`; the library does not guess.

## Rules that keep the pedal predictable

- Every frame carries a checksum the pedal verifies: a wrong one is silently dropped (no
  reply). The library computes it; if a command times out, nothing happened.
- Writes go to the **edit buffer** (RAM); `mk300 load N` discards them. `save` / `copy` write
  flash and refuse a slot that already has a name unless `--overwrite` is given. After a flash
  write the pedal is busy for a few seconds; the library waits for the slot to read back.
- Global settings: write only the fields listed in `mk300 global`, one at a time.
- The editor does not follow changes made over USB; its **Sync** button re-reads the buffer.

## Requirements

macOS (CoreMIDI through `python-rtmidi`), Python ≥ 3.11, the pedal on USB (port `USB Composite
Device`). The editor can stay open. [tone-analyzer](https://github.com/jpfaria/tone-analyzer)
is installed as a dependency (the tone-builder skill measures with it).

## Claude Code plugin

This repo is also a plugin marketplace with two skills: `mk300` (configure the pedal: the CLI
and the rules above) and `tone-builder` (build the tone of a song as a preset from cited gear
research).

```bash
claude plugin marketplace add jpfaria/mvave-mk-300
claude plugin install mk300@mvave-mk-300
```

## Development

```bash
pip install -e ".[dev]" && pytest -q      # golden vectors captured from the editor (docs/captures)
python3 tools/build_reference.py           # regenerate skills/mk300/reference.md and docs/catalog.md
```
