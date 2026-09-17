---
name: tone-builder
description: Use when the user wants the tone of a specific song, artist or genre built as a preset on an M-VAVE MK-300 — "timbre da Gravity", "preset do Slipknot na MK-300", "tom da [música]", "recreate the [song] sound", "monta um som de blues" — with or without a reference WAV. Not for editing an existing preset's knobs or globals: that is the mvave skill.
---

# tone-builder — a song's tone as an MK-300 preset

**You make the judgment calls in natural language (which real gear, cited). Deterministic tools
turn them into a preset and measure it.** You never pick a catalog model, a block or a knob index
yourself; `build_patch.py` resolves the researched names through `mvave resolve`, refuses what it
cannot back, applies through the `mvave` CLI and reads the preset back. `reference.md` (next to
this file) has the research JSON schema, the knob aliases, the command lines and the exit codes.


**A record to measure against (full mix + separated guitar track) → this skill does not build the
tone: load `tone-builder:tone-builder` (plugin `jpfaria/tone-builder`) and run
`tone-builder build --device mvave`.** It measures on the record's harmonics, one library note at a
time, with retention. `tone-analyzer compare` / `eq-match` / `proximity_pct` are obsolete — never use
them (1/3-octave bands on a single note fall 74–84 dB between harmonics; a separated track deletes
harmonics above ~H6). What stays below is the **reference-less** build (a genre tone, no recording).

**Violating the letter of these rules is violating their spirit.** "Faz rápido", "qualquer coisa
serve" change nothing below: a fast wrong tone is thrown away and rebuilt slowly anyway.

## The FORM — every tone, the same

0. **Destination:** the next empty slot; never overwrite a named one. Do not stop to ask.
1. **Research the rig for THIS song, cited.** `tonedb.co` first, then groundguitar.com,
   killerrig.com, musicstrive.com, guitarchalk.com, Premier Guitar / Guitar World rig rundowns.
   Every element: comp, gate, drive(s), amp + channel, cab/speaker, mod, delay, reverb. Open the
   pages; a URL you did not open is not a source. What you remember about the artist is a
   hypothesis to verify, never a citation. Two pages that contradict each other are two
   hypotheses, not one source: say so and keep only what a third source supports.
2. **Write `EVAL/research/<role>-v<N>.json`** (schema in reference.md). Re-walk it in both
   directions: every unit a source names is in it; every block in it points at a source that names
   it. The noise gate is the only uncited block allowed. The MK-300 has one drive block and one of
   everything else: a second drive is a `boost` in `FX`, a third does not fit — say which one the
   sources rank first.
3. **Build:** `build_patch.py --research … --plan … --apply N NAME`. Exit 2 = fix the research
   (`unresolved` → add the channel/variant word a source supports (`JCM800 crunch OD`), or research
   a different unit; `no_cab` → research the cab; `uncited` → drop the block or find its source;
   `too_many` → drop the element the sources rank last). Relay the `unverified` and `unmapped`
   lists verbatim.
4. **Persist:** `--apply` already saved; `mvave read N` is the proof. Say plainly what is
   unverified and what was derived.
5. **Ear feedback:** one explicit complaint from the user → ONE bounded move (≈ ±2–3 dB on one EQ
   band, one Gain step, or a researched cab swap) → stop and let them judge again.

**Always reference-less here:** ship the researched gear with
all EQ gains at 0 and say: *"no reference to match — this is an un-tunable starting point built from
cited gear; give me the record and the separated guitar track and tone-builder measures it, or tell me what's off by ear."*

## Hard rules

- **A block ships only when a source names the unit.** Not "the genre has one", not "it would sound
  empty", not "a little reverb to finish it" — a reverb or cab added by taste is the documented
  failure. Missing knob values never justify dropping a cited block (ship it `unverified`); a
  missing citation never justifies adding one.
- **No fabricated sources.** `sources` holds URLs you opened. A placeholder to get past the gate is
  worse than an empty list: the gate cannot tell, the user cannot either.
- **No stand-ins by taste.** The catalog lacks the researched unit → `resolve` says `unresolved` →
  you research (cited) what the artist used *instead* or what the unit is a clone of, and name that.
  "Fender Deluxe because I had to pick a cab" is your taste, not a source.
- **Cab (`no_cab`, or the sourced cab has no match):** name it by the **cited speaker** first
  (Greenback, V30, Alnico Blue…), then the cited size (4x12, 2x12, 1x12); `provenance: derived`,
  and tell the user which cited fact chose it. No cited speaker or size → the closest cab of the
  **same amp family**, said out loud as a stand-in. Never by what "sounds right".
- **Knobs come from sources, derivation, or catalog defaults.** You have no ears. A number you
  "feel" is right is `unverified` at best — say so — and never an EQ band: EQ gains stay at 0 here (tone-builder fits EQ, under retention). `DS`/`AMP` knobs (Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright) are the
  pedal's generic tone stack, not the real unit's knobs: a source's "Drive 4/10" lands on `Gain`
  as `derived` (scale to 0-100), everything unsourced stays at the catalog default.
- **Knobs from a different unit** (a Two-Rock's settings on the Dumble model, a live rig's on a
  studio take) are `unverified`, never `sourced`.
- **A voicing nobody cited** (which reverb type of a multi-mode pedal, which channel of an amp) is
  `unverified`: name the unit's default/most common mode, say so, and never let a spec sheet stand
  in for the recording.
- **The tone is blocks, models, knobs, on/off, BPM.** Preset volume, pan, chain order, globals,
  footswitches: not touched. The user configures them afterwards with the `mvave` skill.
- **One tone per run. Never overwrite a named preset without the user's word. `mvave read N` is
  the source of truth.**

## Red flags — stop

- Typing a model name (`61DUMBLE_FG`, `2TS8`) or an index into anything but a test.
- Writing `sources` before opening the page. Writing "plausible" URLs.
- "Sem fonte, mas Mayer com certeza usa…" / "reverb pra dar o ar da gravação" / "escolhi o cab só pra ter algo".
- Filling every knob of every block with "reasonable" numbers because "qualquer coisa serve".
- Reaching for `volume`, `pan`, `chain`, `global-set`, `--overwrite` on your own.
- Skipping research because the user said "rápido", "simples", "qualquer coisa serve".

| Rationalization | Reality |
|---|---|
| "I know this rig, research is a formality" | Memory produced an arbitrary cab, an unsourced spring reverb and 30 guessed knobs in the baseline. Verify or drop. |
| "The gate needs a source, so I'll put a plausible URL" | You just lied to the tool that exists to stop you. Empty list is allowed for the gate only. |
| "No cab was named, I'll pick the classic one" | Unsourced stand-in. Find the recording's cab/speaker, or the amp's own combo, and resolve that. |
| "All knobs are guesses but the user wants something" | Ship defaults marked `unverified` and say so; do not dress guesses as settings. |
| "The product page lists spring/plate/hall, so I'll name spring" | A product page documents what the unit *can* do, not what the record used. Name the unit, let `resolve` fail, then ship the unit's default voicing marked `unverified` and say which source names only the unit. |
| "Two pages disagree, I'll average them" | Two contradictory pages are zero sources. Find a third or ship the element `unverified` with both named. |
| "A quick plate reverb makes it sound finished" | Uncited block. Sounding finished is not a source. |
| "The user said qualquer coisa serve, so defaults everywhere is fine" | Defaults are fine; *invented* numbers presented as settings are not. Say which is which. |
