"""The only file that knows the `tone-analyzer` CLI (github.com/jpfaria/tone-analyzer, v0.1).

  tone-analyzer analyze REF --out-dir D          -> D/fingerprint.json  (fingerprint_match_target.self_floor_pct,
                                                     .top_octave_dead, .reliable_range_hz)
  tone-analyzer compare REF WET --out-dir D      -> D/diff.json         (proximity_pct, ref_top_octave_dead)
  tone-analyzer eq-match REF WET --gains g1,..,g8 --output F -> F      (new_gains[8], band_centers_hz[8])
The analyzer works on 8 octave bands (80 Hz .. 10.24 kHz); the pedal's Normal EQ 10 has 10 (31 Hz .. 16 kHz).
This module maps between them by nearest centre. Override the executable with $TONE_ANALYZER.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

TONE_ANALYZER = os.environ.get("TONE_ANALYZER", "tone-analyzer")
GRAPHIC_EQ_HZ = [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]   # Normal EQ 10
ANALYZER_BANDS_HZ = [80, 160, 320, 640, 1280, 2560, 5120, 10240]
EQ_CAP_DB = 6.0
WITHIN_MARGIN = 3.0
DEGRADED_ROLLOFF_HZ = 800


def _run(args: list[str], out_dir) -> tuple[int, str]:
    p = subprocess.run([TONE_ANALYZER, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _call(run, args: list[str], out_dir, result_name: str) -> dict:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    code, out = run(args, out_dir)
    if code != 0:
        raise SystemExit(f"{TONE_ANALYZER} {' '.join(args)} failed: {out.strip()}")
    return json.loads((Path(out_dir) / result_name).read_text())


def fingerprint(ref, out_dir, run=_run) -> dict:
    """self_floor_pct (the per-song ceiling), top_octave_dead, degraded (-> flat-EQ path, no loop)."""
    fp = _call(run, ["analyze", str(ref), "--out-dir", str(out_dir)], out_dir, "fingerprint.json")
    g = fp.get("fingerprint_match_target") or fp.get("global") or fp
    dead = bool(g.get("top_octave_dead", False))
    hi = (g.get("reliable_range_hz") or [0, 20000])[1]
    return {"self_floor_pct": float(g.get("self_floor_pct", 100.0)), "top_octave_dead": dead,
            "degraded": dead or hi < DEGRADED_ROLLOFF_HZ}


def compare(ref, wet, out_dir, run=_run) -> dict:
    d = _call(run, ["compare", str(ref), str(wet), "--out-dir", str(out_dir)], out_dir, "diff.json")
    return {"proximity_pct": float(d["proximity_pct"]), "ref_top_octave_dead": bool(d.get("ref_top_octave_dead", False))}


def within(proximity_pct: float, self_floor_pct: float) -> bool:
    """The acceptance bar: within 3 points of the reference's own self-similarity floor."""
    return proximity_pct >= self_floor_pct - WITHIN_MARGIN


def _nearest(hz: float, centres: list[float]) -> int:
    return min(range(len(centres)), key=lambda j: abs(centres[j] - hz))


def to_analyzer_bands(eq_gains: list[float], bands: list[float] = ANALYZER_BANDS_HZ) -> list[float]:
    """Current 10 Graphic EQ gains -> the analyzer's 8 band gains (nearest Graphic EQ band per analyzer centre)."""
    return [float(eq_gains[_nearest(hz, GRAPHIC_EQ_HZ)]) for hz in bands]


def to_graphic_eq(new_gains: list[float], bands: list[float]) -> list[float]:
    """Analyzer band gains -> 10 Graphic EQ gains (nearest analyzer centre per Graphic EQ band), capped ±6 dB."""
    return [max(-EQ_CAP_DB, min(EQ_CAP_DB, float(new_gains[_nearest(hz, bands)]))) for hz in GRAPHIC_EQ_HZ]


def eq_match(ref, wet, eq_gains: list[float], out_dir=".", run=_run) -> list[float]:
    """Next 10 Graphic EQ gains (dB, capped ±6) that move WET's spectral shape toward REF."""
    out = Path(out_dir) / "eq_match.json"
    args = ["eq-match", str(ref), str(wet), "--gains", ",".join(f"{g:g}" for g in to_analyzer_bands(eq_gains)),
            "--output", str(out)]
    r = _call(run, args, out_dir, out.name)
    bands = [float(b) for b in (r.get("band_centers_hz") or r.get("bands_hz") or ANALYZER_BANDS_HZ)]
    return to_graphic_eq([float(x) for x in r["new_gains"]], bands)
