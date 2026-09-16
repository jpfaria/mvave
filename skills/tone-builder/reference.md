# tone-builder reference

Two tools, used only from the command line:

- `mvave` — the pedal. `resolve` (catalog lookup), `reamp` (USB audio through the pedal), and the
  preset commands `build_patch.py` drives. Everything about the pedal itself is in the `mvave` skill.
- `tone-analyzer` — the audio (github.com/jpfaria/tone-analyzer, Python ≥ 3.11). `analyze` /
  `compare` / `eq-match` on WAV files. Override the executable with `$TONE_ANALYZER`. Its interface
  lives in `scripts/analyzer.py` (see its docstring); when the CLI changes, fix that one file.

Setup: `tone-analyzer` is a dependency of `mvave` (installed with it); the re-amp loop also needs
`pip install "mvave[reamp]"`. Check `mvave resolve AMP "Fender Twin"` and `tone-analyzer --help`
before starting a tone; missing → install, do not improvise.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/tone-builder/scripts/` (stdlib only, Python ≥ 3.11).

## Research JSON

Written by the agent. It carries **gear names and sources**, never catalog model names, block ids
or knob indices.

```json
{
  "song": "Gravity", "artist": "John Mayer", "role": "rhythm",
  "id": "john_mayer_gravity_rhythm", "name": "John Mayer - Gravity (rhythm)",
  "tempo_bpm": 66,
  "amp":    { "name": "Dumble Overdrive Special", "brand": "dumble",
              "params": { "gain": 35 }, "provenance": "sourced", "sources": ["https://…"] },
  "drives": [ { "name": "Ibanez TS808", "brand": "ibanez", "params": { "gain": 20, "level": 60 },
                "provenance": "sourced", "sources": ["https://…"] } ],
  "cab":    { "name": "Marshall 1960 4x12", "params": {}, "provenance": "derived", "sources": ["https://…"] },
  "fx":     [ { "type": "gate", "name": "noise gate", "params": { "threshold": -40 },
                "provenance": "unverified", "sources": [] },
              { "type": "delay", "name": "analog delay",
                "params": { "time_ms": 454, "feedback": 28, "mix": 30 },
                "provenance": "derived", "sources": ["https://…"] } ]
}
```

| Field | Rule |
|---|---|
| `amp.name` | Real amp + channel/voicing words when the catalog has variants: the MK-300 names end in `_CL` (clean), `_OD`/`_CR`/`CRUNCH` (crunch), `_DS` (distortion), `_HV`/`_TDS`/`_MT` (high gain), `_CH1/2/3`, `LEAD`. `resolve` reports a tie between voicings as `unresolved`: add the word the sources support (`"JCM800 crunch OD"`). Ties between captures of the same voicing (`_57`, `_196`, `_FG`, `_ECM` = mic / era variants) resolve to the first. |
| `drives[]` | One entry per pedal, signal order. The first lands in `DS` (the pedal's only drive block, generic 8-knob tone stack), the second in `FX` as a boost (`FX` has Boost / A Boost / E Boost / B Boost / Boost ED), a third is `too_many`. `[]` = clean. |
| `cab` | Mandatory (`no_cab` otherwise): the AMP models have no speaker. Name the cited cab or speaker (`"Marshall 1960 4x12"`, `"Vox AC30 Alnico Blue"`, `"Fender Deluxe 1x12"`). For a combo, the amp's own cab with `provenance: derived`. |
| `fx[].type` | `gate`, `comp`, `wah`, `mod`, `delay`, `reverb`, `eq`. `volume` and `limiter` are rejected. One of each: the MK-300 has one block per type. |
| `sources` | Real URLs you opened. Placeholders, "plausible" URLs, or citations from memory are forbidden — the gate cannot check them, you can. Empty `sources` is only allowed on the `gate`. |
| `provenance` | `sourced` (a source states the knob values), `derived` (computed: delay time from BPM, cab from the amp, a 0-10 dial scaled to 0-100), `unverified` (cited unit, knobs unknown → catalog defaults). Absent = `unverified`. |
| `params` | Keys are generic knob names (alias table below); values in the pedal's units (0–100 knobs, delay `time` in ms, `speed` in Hz — the script stores it x10, thresholds in dB). Unknown keys are reported as `unmapped` and ignored. |

**Knob aliases** (`params` key → model knob it lands on, first match by prefix): `gain|drive` → Gain/Drive/Sustain/Fuzz;
`level|volume|output` → Level/Volume/Output; `tone`; `bass|low`; `mid|middle`; `treble|high`; `presence` → Pres;
`resonance` → Reso; `bright`; `time|time_ms` → Time; `feedback|repeats` → Fb; `mix|blend`; `depth`; `rate|speed` → Speed;
`threshold` → Thd/Gate; `attack`; `release`; `decay`. Any other key is `unmapped`. Run `mvave params BLOCK MODEL` to see a model's knobs.

## Catalog rules that differ from a modeler with free slots

- **Fixed chain** `WAH FX GATE DS AMP CAB EQ MOD DLY REV VOL`; every researched element lands in
  its block, blocks with nothing researched are switched off, `VOL` is never touched.
- **AMP models have no speaker.** `cab` is mandatory; the build enforces it.
- The EQ block is always `Normal EQ 10` (31 Hz … 16 kHz, dB). Gains come only from
  `tone-analyzer eq-match` (`--eq-gains`, capped ±6 dB); otherwise all 0.
- `DS`/`AMP` knobs are the pedal's generic stack (Gain, Level, Bass, Middle, Treble, Reso, Pres,
  Bright); the real unit's dials map onto it as `derived`.
- Preset volume, pan, chain order, globals, footswitches: not this skill — the user configures them
  with the `mvave` skill afterwards.

## Commands

```bash
TB=${CLAUDE_PLUGIN_ROOT}/skills/tone-builder/scripts
python3 $TB/build_patch.py --research R.json --plan PLAN.json                 # plan only, no pedal
python3 $TB/build_patch.py --research R.json --plan PLAN.json --apply 150 NAME [--overwrite] [--eq-gains g1,…,g10]
mvave reamp DI.wav WET.wav [--tail S] [--mono]                                # USB Audio = RESAMPLE for the run
tone-analyzer analyze REF.wav --out-dir EVAL/ref                              # fingerprint.json: self_floor_pct, top_octave_dead
tone-analyzer compare REF.wav WET.wav --out-dir EVAL/v1                       # diff.json: proximity_pct
tone-analyzer eq-match REF.wav WET.wav --gains g1,…,g8 --output EVAL/v1/eq_match.json   # 8 analyzer bands (80 Hz…10.24 kHz)
```

The analyzer works on 8 octave bands, the pedal's Normal EQ 10 on 10: `scripts/analyzer.py`
(`eq_match(ref, wet, current_10_gains)`) does the nearest-centre mapping both ways and caps ±6 dB —
use it (python one-liner or import) rather than mapping by hand.

`build_patch.py` exit codes: `2` build aborted (`unresolved`, `uncited`, `forbidden`, `too_many`, `no_cab`
— stderr says which and why), `4` verify mismatch after apply (`read N` did not read back the plan),
`5` the target preset already has a name and `--overwrite` was not given. It prints the `unverified`
and `unmapped` lists on stderr: relay both to the user.

`--apply` runs: `load N`, `model` per block, `param` per non-default knob, `enable` on/off per block
(never `VOL`), `bpm`, `save N NAME`, then `read N` to verify. Nothing else.

## Re-amp

`mvave reamp` sets the global USB Audio field to RESAMPLE, plays the DI on the pedal's USB audio
output (`USB-Audio`, 44.1 kHz), records the return and restores the field. Exits with "no signal"
when nothing came back.

DI: a real guitar DI WAV, reused across every tone, kept at `$HOME/.mvave/di.wav`. Ask the user for
it once (any dry electric-guitar recording, mono, a few bars of open chords + single notes). The
`tone-analyzer` test fixtures are synthetic tones, not a guitar — never use them as the DI. No DI →
the validation loop is unavailable → reference-less path, say so.

## Evaluation directory

`EVAL = $HOME/.mvave/evaluations/<artist-song-slug>/` (create it). Keep `research/<role>-v<N>.json`,
`plan-v<N>.json`, `wet-v<N>.wav`, the analyzer out-dirs, and `eval.md` (gear research with sources,
mapping, iteration log with the numbers, unverified params, methodology notes).
