"""Regenerate docs/catalog.md and skills/mk300/reference.md from mk300/catalog.json + the CLI."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mk300 import preset as pr  # noqa: E402

cat = json.loads((ROOT / "mk300" / "catalog.json").read_text())

# Hand-written notes: what each block / model family does and what the abbreviations point at.
# Sources: the model names themselves, the editor's knob names, M-VAVE's "MK300 NEW DS LIST" PDF
# (the MW- loadable models) and general knowledge of the modelled units. Everything marked (?) is
# an educated reading of the abbreviation, not something M-VAVE documents.
BLOCK_NOTES = {
    "WAH": "Wah pedal block (needs an expression pedal or the auto/touch variants). X-Wah/Cry-Wah = classic Cry Baby-style sweep; Funk-Wah = vocal funk voicing; Slide-Wah = slower sweep; Wah-Wah = auto-wah (LFO, Speed/Sync); Sense-Wah = envelope (touch) wah driven by picking dynamics.",
    "FX": "Pre-amp utility block: auto/touch wah, lo-fi bit crusher, boosts (clean Boost, A/E/B Boost = tone-stack boosts, Boost ED = gritty edge boost), compressors (Compress = pedal-style, Compress Pro / F Compress = studio ratio/knee), pitch tools (Pitch = dual pitch shifter, Octave = octaver, Ring = ring modulator, Pitch shifter = semitone shift, Whammy = expression-controlled bend).",
    "GATE": "Noise gate / compressor block: AI Gate and AI Ms Gate = adaptive gates (Gate amount + Bias), Soft/Hard Gate = threshold gates, Pro Gate = full envelope (Att/Rel/Thd/Kw/Ratio); the three compressors mirror the FX block ones.",
    "DS": "Drive block: 40 neural/analog captures of overdrive, distortion and fuzz pedals. Knobs are the same for every model: Gain, Level, Bass, Middle, Treble, Reso (low resonance), Pres (presence), Bright. The number prefix is the model's 1-based position. Extra 'MW-' models (MW-808 = TS808, MW-GOLD = Klon Centaur, MW-OCD, MW-SD1, MW-DS1, MW-RAT, MW-XEP = EP Booster, MW-FACE = Fuzz Face, MW-HRZ = Horizon Precision Drive, MW-EQP = EQD Plumes, MW-MUFF = Big Muff, MW-B7000 = Darkglass B7K Ultra) are downloadable .am3Data files loaded through the editor's Sounds page, not part of this fixed list.",
    "AMP": "Amp block: 120 captures, same 8 knobs as DS (Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright). 1-100 guitar, 101-120 bass (_BS). Suffixes: _CL clean, _OD overdrive/crunch, _DS distortion, _HV/_HDS high gain, _TDS/_MT metal, _FG/_57/_196/_ECM = variants captured with different cabs/mics or era (57 = SM57?, 196x = '60s circuit?).",
    "CAB": "Cabinet IR block (100 IRs, 1024/2048 pts): Level, Low Cut, High Cut. 1-64 guitar cabs, 65-80 combos/specials, 81-100 bass cabs. Third-party IRs can be imported through the editor.",
    "EQ": "Graphic EQ block: Guitar EQ 6 (100 Hz-3.2 kHz), Bass EQ 7 (50 Hz-10 kHz), Normal EQ 10 (31 Hz-16 kHz). Bands in dB, stored as signed integers (0 = flat).",
    "MOD": "Modulation block. Tri = triangle-LFO variant, Opto = optical-style, Univibe = vibe; Autofilter = envelope/LFO filter; the 'Stereo' models are separate algorithms with their own knobs (Phaser Stereo has Stage/Regen/Lfo shape, Chorus Stereo has Mode, Vibrato Stereo has Bits).",
    "DLY": "Delay block: 13 mono algorithms (Clean = digital, Modern = digital with Phaser/Mod, Echo = tape-ish, Analog = BBD, Duck = ducking, Dtype = tape with Grit, Tremolo, Filter, Dual, Lofi, Pattern = rhythmic multi-tap, Ice = pitch-shifted, Reverse) plus PingPong Stereo and the same 13 in stereo. Time is in ms (or a note division when Sync is on).",
    "REV": "Reverb block: Room, Hall, Plate, Spring, Shimmer (pitch-shifted tail), Bloom (swelling ambient), Cloud (diffuse), Lofi (sample-rate/noise), Swell (volume-swell reverb), each also in stereo.",
    "VOL": "Volume block (single model, one knob) - the pedal's post volume, usually assigned to the expression pedal.",
}

BASED_ON = {  # model name -> what the abbreviation points at (readings of the names; '?' = guess)
    "AMP": {"J120": "Roland JC-120 (clean)", "J800": "Marshall JCM800", "J900": "Marshall JCM900", "J2000": "Marshall JCM2000", "JVM": "Marshall JVM",
            "MAR": "Marshall", "UK": "Marshall-style UK", "PLX": "Marshall Plexi", "FD": "Fender", "VXO": "Vox AC30/AC15", "MES": "Mesa Boogie (Mark / Rectifier)",
            "OR": "Orange", "LANY": "Laney", "BOG": "Bogner", "EHV5150": "EVH 5150 III", "XC": "?", "RADAL": "Randall", "DUMBLE": "Dumble ODS",
            "ROLANS": "Roland?", "DARK": "Diezel? / dark high gain", "HIGIAN": "generic high gain", "MATTER": "Matchless?", "JHS": "JHS (pedal into amp)?",
            "RAT": "ProCo RAT into amp", "WS": "?", "COOL": "?", "AXE": "?", "M-VAVE": "M-VAVE original", "JOHNS": "?", "HORIZON": "Horizon Devices?",
            "ROOM40": "?", "BLUES": "Bluesbreaker", "MT100": "Marshall MT-100?", "MT80": "?", "BOOSS": "Boss?", "JAZZ": "jazz clean",
            "AgDb750": "Aguilar DB 750 (bass)", "ApSVT": "Ampeg SVT (bass)", "DgM900": "Darkglass Microtubes 900 (bass)", "FenRum": "Fender Rumble (bass)",
            "GkF550": "Gallien-Krueger Fusion 550 (bass)", "HkeHd50": "Hartke HD50 (bass)", "MarkLm": "Markbass Little Mark (bass)", "OrgAd": "Orange AD200 (bass)",
            "PjBuddy": "Phil Jones Bass Buddy", "RolDb": "Roland DB (bass)", "Mb400": "Markbass? 400 (bass)", "DgXu": "Darkglass Exponent? (bass)",
            "ApSp": "Ampeg (bass)", "Mar50": "Markbass? (bass)", "Mark500": "Markbass 500 (bass)", "PjbCub": "Phil Jones Cub (bass)", "Tc21Vt": "Tech 21 VT Bass",
            "WatMod": "Warwick? (bass)", "GKL800": "Gallien-Krueger 800RB (bass)"},
    "DS": {"BLUES_OD": "Bluesbreaker-style OD", "TS8": "Ibanez TS808", "TS-9": "Ibanez TS9", "DS1": "Boss DS-1", "DS2": "Boss DS-2", "SUPA": "Suhr Riot?",
           "RAT": "ProCo RAT", "JHS": "JHS", "MT_": "Boss Metal Zone", "TDS": "Timmy?", "XC": "?", "QC": "?", "HIGAIN": "high gain", "M-BOOSTER": "booster",
           "BIG-DR": "Big drive", "CL_BOOST": "clean boost (Klon-style?)", "BD": "Boss Blues Driver", "M9OS": "?", "M2000": "?", "DS800": "JCM800-in-a-box?",
           "DS900": "JCM900-in-a-box?", "MAR-DS": "Marshall-style distortion", "BOG_DS": "Bogner-style", "SONDO": "?", "MID-BOST": "mid boost",
           "RED_DS": "?", "MODEN_DS": "modern distortion", "SuperOD": "Boss SD-1?", "BLUES_DR": "Boss Blues Driver", "Black-BOX": "?", "BIG-MUFF": "EHX Big Muff Pi",
           "PLX": "Plexi-in-a-box", "M-VAVE": "M-VAVE original"},
    "CAB": {"AC-": "Vox AC (Celestion/Alnico)", "JVM_1960": "Marshall 1960 4x12", "DELUXE": "Fender Deluxe", "BOG": "Bogner", "FD": "Fender", "HESS": "?",
            "HIW": "Hiwatt", "MAR": "Marshall", "MESA": "Mesa 4x12", "WANGS": "Wangs", "V30": "Celestion Vintage 30", "VOX": "Vox", "M160": "Beyer M160 mic",
            "MD421": "Sennheiser MD421 mic", "EV": "Electro-Voice", "G12-EVH": "Celestion G12 EVH", "BGN": "Bogner", "Recto": "Mesa Rectifier", "FRMAN": "Friedman",
            "OR_": "Orange", "Ranll": "Randall", "RE_SUPER": "?", "EGNL": "Engl", "MeOSick/MesaOSick": "Mesa Oversized", "Sold": "Soldano", "Pey": "Peavey",
            "MRSH": "Marshall", "VA5153": "EVH 5153", "Cele": "Celestion", "Die": "Diezel", "EAGL": "Engl?", "Vx": "Vox", "Fen": "Fender", "Alton": "?",
            "Og": "Orange", "HaBton": "Harley Benton", "Elctrovoice": "Electro-Voice", "Rolnd": "Roland JC", "Mess": "Mesa", "WS212": "?", "Agula": "Aguilar",
            "Ampg": "Ampeg", "Ash": "Ashdown", "Bareface": "Barefaced", "Bstert": "?", "DavEend": "David Eden", "Dg": "Darkglass", "Fd": "Fender", "GK": "Gallien-Krueger",
            "Hark": "Hartke", "Mb": "Markbass", "Ran": "?", "SR": "?", "Tace": "Trace Elliot"},
}

lines = ["# MK-300 model catalog", "",
         "Generated by `tools/build_reference.py` from `mk300/catalog.json` (M-EFCS 3.7.1413 dropdowns, "
         "knob names from the editor's panel, defaults read from the pedal on firmware V73, 2026-09-16). "
         "The model **index** is the value written to the block's model byte (`mk300 model BLOCK index|name`). "
         "Knob values are int16; Speed knobs are stored x10 (2.5 -> 25), delay Time in ms, EQ bands in dB.", ""]
for blk in cat["blocks"]:
    name = blk["name"]
    lines += [f"## {name} (block id {blk['id']}, {len(blk['models'])} models)", "", BLOCK_NOTES.get(name, ""), ""]
    if name in BASED_ON:
        lines += ["Name fragments and what they point at (readings of the abbreviations, `?` = unsure):", ""]
        lines += ["| fragment | based on |", "|---|---|"] + [f"| `{k}` | {v} |" for k, v in BASED_ON[name].items()] + [""]
    lines += ["| # | model | knobs (index: name = default) |", "|---|---|---|"]
    for m in blk["models"]:
        knobs = m.get("knobs") or []
        dflt = m.get("defaults") or []
        ks = ", ".join(f"{i}: {k}" + (f" = {dflt[i]}" if i < len(dflt) else "") for i, k in enumerate(knobs))
        lines.append(f"| {m['index']} | {m['name']} | {ks} |")
    lines.append("")
(ROOT / "docs" / "catalog.md").write_text("\n".join(lines))

help_txt = subprocess.run([sys.executable, "-m", "mk300"], capture_output=True, text=True, cwd=ROOT, env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}).stdout
ref = ["# mk300 reference", "", "## Commands", "", "```", help_txt.strip(), "```", "",
       "## Preset struct (edit buffer, space 1, 448 bytes)", "",
       "| offset | field |", "|---|---|",
       "| 0x00 | name, 20 bytes |", "| 0x18 | volume u16 |", "| 0x1A | bpm u16 |", "| 0x1C | pan i16 (0 = C) |",
       "| 0x20 | chain order, 11 block ids |", "| 0x2B + block | on/off |", "| 0x36 + block | model index |",
       "| 0x42 + 24*block + 2*knob | knob i16 |", "",
       "Blocks: " + ", ".join(f"{i} {n}" for i, n in enumerate(pr.BLOCKS)), "",
       "## Global block (space 2, 86 bytes)", "",
       "| offset | field | values |", "|---|---|---|",
       "| 0x00 | current preset index (0-based) | |", "| 0x38 | A/B Convert | 0 OFF, 1 ON |",
       "| 0x3C | RCH (right channel output) | 0 Nor, 1 Dry, 2 NoCAB |", "| 0x3D | USB Audio | 0 ON, 1 OFF, 2 RESAMPLE, 3 DRY |", "",
       "Only these were seen written by the editor; write nothing else in space 2.", "",
       "## Model catalog", ""]
for blk in cat["blocks"]:
    ref.append(f"### {blk['name']}")
    ref.append("")
    for m in blk["models"]:
        ref.append(f"- {m['index']} {m['name']}: " + ", ".join(m.get("knobs") or []))
    ref.append("")
(ROOT / "skills" / "mk300" / "reference.md").write_text("\n".join(ref))
print("wrote docs/catalog.md", len(lines), "lines; skills/mk300/reference.md", len(ref), "lines")
