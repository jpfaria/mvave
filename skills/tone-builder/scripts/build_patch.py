#!/usr/bin/env python3
"""research JSON -> resolve (mk300 resolve) -> gate -> plan -> apply (mk300 CLI).

Stdlib only. Talks to the pedal ONLY through the `mk300` command line; never imports it.
The MK-300 has a fixed chain of 11 blocks (WAH FX GATE DS AMP CAB EQ MOD DLY REV VOL): every
researched element lands in its block; blocks with nothing researched are switched off.
Exit codes: 2 build aborted (see reason), 4 verify mismatch, 5 target preset is named (no --overwrite).
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

BLOCKS = ["WAH", "FX", "GATE", "DS", "AMP", "CAB", "EQ", "MOD", "DLY", "REV", "VOL"]
BLOCK_FOR = {"gate": "GATE", "comp": "FX", "wah": "WAH", "drive": "DS", "boost": "FX", "amp": "AMP",
             "cab": "CAB", "eq": "EQ", "mod": "MOD", "delay": "DLY", "reverb": "REV"}
FORBIDDEN_TYPES = {"volume", "limiter"}
EQ_MODEL = ("EQ", "Normal EQ 10")
EQ_CAP_DB = 6.0
KNOB_ALIASES = {
    "gain": ("gain", "drive", "sustain", "fuzz"), "drive": ("drive", "gain"), "level": ("level", "volume", "output"),
    "volume": ("volume", "level", "output"), "output": ("output", "volume", "level"), "tone": ("tone",),
    "bass": ("bass", "low"), "low": ("low", "bass"), "mid": ("middle", "mid"), "middle": ("middle", "mid"),
    "treble": ("treble", "high"), "high": ("high", "treble"), "presence": ("pres",), "bright": ("bright",),
    "resonance": ("reso",), "time": ("time",), "time_ms": ("time",), "feedback": ("fb", "feedback", "repeat"),
    "repeats": ("fb", "feedback"), "mix": ("mix", "blend"), "blend": ("blend", "mix"), "depth": ("depth",),
    "rate": ("speed", "rate"), "speed": ("speed", "rate"), "threshold": ("thd", "gate", "threshold"),
    "attack": ("attack", "att"), "release": ("release", "rel"), "decay": ("decay",), "sync": ("sync",),
}
SPEED_X10 = ("speed",)          # knobs stored x10 (Speed 2.5 -> 25)


class BuildError(SystemExit):
    def __init__(self, reason: str, detail: str):
        super().__init__(2)
        self.reason, self.detail = reason, detail

    def __str__(self):
        return f"{self.reason}: {self.detail}"


class Runner:
    """Runs `mk300 ...`; injectable for tests."""
    exe = "mk300"            # may be a command line, e.g. "python3 -m mk300"

    def run(self, args: list[str]) -> tuple[int, str]:
        p = subprocess.run([*shlex.split(self.exe), *args], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr


@dataclass
class Knob:
    index: int
    name: str
    value: float
    origin: str            # research | derived | default | eq


@dataclass
class Slot:
    block: str
    model: str
    model_index: int
    role: str
    knobs: list[Knob]
    provenance: str
    sources: list[str]


@dataclass
class Plan:
    name: str
    slots: list[Slot]
    tempo: int | None
    unverified: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def load_research(path: Path) -> dict:
    return json.loads(Path(path).read_text())


_RESOLVE_LINE = re.compile(r"^\s*([0-9.]+)\s+(\d+)\s+(\S.*?)\s*$")


def _resolve(runner: Runner, block: str, name: str) -> tuple[int, str]:
    """`mk300 resolve BLOCK NAME` prints `score index name` lines. Strict: the best score must be
    unique (a tie between different units is `unresolved`); nothing found is `unresolved`."""
    code, out = runner.run(["resolve", block, name, "-n", "5"])
    rows = [(float(m[1]), int(m[2]), m[3]) for m in map(_RESOLVE_LINE.match, out.splitlines()) if m]
    if code != 0 or not rows:
        raise BuildError("unresolved", f"{name!r} in {block}: no model matches (research what it is a clone of)")
    best = [r for r in rows if r[0] == rows[0][0]]
    if len(best) > 1 and len({_voicing(r[2]) for r in best}) > 1:
        raise BuildError("unresolved", f"{name!r} in {block} ties between {[r[2] for r in best]}: add the channel/variant word a source supports")
    return rows[0][1], rows[0][2]


VOICING = {"CL", "OD", "OD2", "OD3", "DS", "HV", "CR", "TR", "MT", "TDS", "HDS", "RED", "HOT", "BST", "CH1", "CH2", "CH3",
           "LEAD", "LEAD2", "LEAD3", "SOLO", "CRUNCH", "SWEET", "BR", "METEL", "BOOST", "BLUES", "JZCL"}


def _voicing(model: str) -> str:
    """The channel/voicing tokens of a model name (21J800_CL_196 -> 'CL'); mic/era suffixes ignored,
    so a tie between two captures of the same voicing is fine and a CL/OD/DS tie is not."""
    toks = re.split(r"[_\-]", re.sub(r"^\d+", "", model).upper())
    return " ".join(t for t in toks if t in VOICING)


_PARAM_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s+default\s+(\S+)")


def _params(runner: Runner, block: str, model: str) -> list[tuple[int, str, float]]:
    code, out = runner.run(["params", block, model])
    if code != 0:
        raise BuildError("unresolved", f"params of {block} {model!r}: {out.strip()}")
    rows = []
    for line in out.splitlines():
        m = _PARAM_LINE.match(line)
        if m:
            try:
                d = float(m[3])
            except ValueError:
                d = 0.0
            rows.append((int(m[1]), m[2].strip(), d))
    return sorted(rows)


def _knobs(runner: Runner, block: str, model: str, params: dict | None, unmapped: list[str], origin: str) -> list[Knob]:
    knobs = [Knob(idx, name, default, "default") for idx, name, default in _params(runner, block, model)]
    for key, value in (params or {}).items():
        target = None
        for cand in KNOB_ALIASES.get(key.lower(), (key.lower(),)):
            target = next((k for k in knobs if k.name.lower().startswith(cand)), None)
            if target:
                break
        if target is None:
            unmapped.append(f"{model}.{key}")
            continue
        v = float(value)
        if target.name.lower().startswith(SPEED_X10):
            v *= 10
        target.value, target.origin = v, origin
    return knobs


def build_plan(research: dict, runner: Runner, eq_gains: list[float] | None = None) -> Plan:
    unverified: list[str] = []
    unmapped: list[str] = []
    blocks: dict[str, tuple] = {}   # block -> (role, name, model_index, model, params, provenance, sources)

    def place(role: str, entry: dict, block: str | None = None):
        block = block or BLOCK_FOR.get(role)
        if block is None:
            raise BuildError("forbidden", f"unknown fx type {role!r}")
        if block in blocks:
            raise BuildError("too_many", f"two elements want the {block} block: {blocks[block][1]!r} and {entry.get('name')!r} (the MK-300 has one {block})")
        idx, model = _resolve(runner, block, entry["name"])
        blocks[block] = (role, entry["name"], idx, model, entry.get("params"), entry.get("provenance", "unverified"), list(entry.get("sources", [])))

    def cite(entry: dict, role: str):
        if role != "gate" and not entry.get("sources"):
            raise BuildError("uncited", f"{role} {entry.get('name')!r} has no source")
        if (entry.get("provenance") or "unverified") == "unverified" and entry.get("params"):
            unverified.append(entry.get("name", role))

    for fx in research.get("fx", []):
        if fx["type"] in FORBIDDEN_TYPES:
            raise BuildError("forbidden", f"{fx['type']} block {fx.get('name')!r}")
    drives = research.get("drives", [])
    for i, d in enumerate(drives):
        cite(d, "drive")
        # first drive -> DS; a second one only fits the FX block as a boost
        place("drive" if i == 0 else "boost", d, "DS" if i == 0 else "FX")
    amp = research["amp"]
    cite(amp, "amp")
    place("amp", amp)
    cab = research.get("cab")
    if cab:
        cite(cab, "cab")
        place("cab", cab)
    else:
        raise BuildError("no_cab", "the MK-300 AMP block has no speaker: research the cab/speaker (or the amp's own combo cab) and name it in `cab`")
    for fx in research.get("fx", []):
        cite(fx, fx["type"])
        place(fx["type"], fx)
    if "EQ" not in blocks:
        blocks["EQ"] = ("eq", "Normal EQ 10", None, EQ_MODEL[1], None, "derived", [])

    slots = []
    for block in BLOCKS:
        if block not in blocks:
            continue
        role, _name, idx, model, params, prov, sources = blocks[block]
        if idx is None:
            idx, model = _resolve(runner, block, model)
        origin = "derived" if prov == "derived" else "research"
        knobs = _knobs(runner, block, model, params, unmapped, origin)
        if role == "eq" and block == "EQ":
            gains = [max(-EQ_CAP_DB, min(EQ_CAP_DB, float(g))) for g in (eq_gains or [0.0] * 10)]
            for k, g in zip(knobs, gains):
                k.value, k.origin = g, "eq"
        slots.append(Slot(block, model, idx, role, knobs, prov, list(sources)))
    return Plan(research.get("name", research.get("id", "tone")), slots, research.get("tempo_bpm"), unverified, unmapped)


def _fmt(v: float) -> str:
    return f"{int(round(v))}"


def apply_plan(plan: Plan, preset: str, name: str, runner: Runner, overwrite: bool = False) -> list[list[str]]:
    """Push the plan into PRESET (1..160) through the mk300 CLI; returns every command run, in order."""
    cmds: list[list[str]] = [["read", preset]]
    _code, out = runner.run(cmds[0])
    first = out.splitlines()[0] if out.strip() else ""
    current = first.split("]", 1)[1].split("   ")[0].strip() if "]" in first else ""
    if current and not current.startswith("USER PRESET") and not overwrite:
        print(f"preset {preset} is named {current!r}: pass --overwrite to replace it", file=sys.stderr)
        raise SystemExit(5)
    used = {s.block for s in plan.slots}
    seq = [["load", preset]]
    for s in plan.slots:
        seq.append(["model", s.block, s.model])   # by name: a bare number is read as the name prefix ("60" -> 60RADAL_HDS), not the index
    for s in plan.slots:
        for k in s.knobs:
            if k.origin != "default":
                seq.append(["param", s.block, str(k.index), _fmt(k.value)])
    for b in BLOCKS:
        if b == "VOL":
            continue
        seq.append(["enable", b, "on" if b in used else "off"])
    if plan.tempo:
        seq.append(["bpm", str(int(plan.tempo))])
    seq.append(["save", preset, name[:20], *(["--overwrite"] if overwrite else [])])
    for c in seq:
        code, out = runner.run(c)
        if code != 0:
            raise SystemExit(f"mk300 {' '.join(c)} failed: {out.strip()}")
    return cmds + seq


_SHOW = re.compile(r"^\s*(on |off)\s+(\S+)\s+(\d+):(\d+)\s+(\S.*?)\s{2,}(.*)$|^\s*(on |off)\s+(\S+)\s+(\d+):(\d+)\s+(\S+)\s*$")


def verify_plan(plan: Plan, preset: str, runner: Runner) -> list[str]:
    """Read PRESET back with `read` and list every model/knob that differs from the plan."""
    _code, out = runner.run(["read", preset])
    seen = {}
    for line in out.splitlines():
        m = re.match(r"^\s*(on |off)\s+(WAH|FX|GATE|DS|AMP|CAB|EQ|MOD|DLY|REV|VOL)\s+(\d+):(\d+)\s+(.*)$", line)
        if not m:
            continue
        rest = m[5]
        vals = dict(kv.rsplit("=", 1) for kv in re.findall(r"\S+=\S+", rest))
        seen[m[2]] = (m[1].strip() == "on", int(m[4]), vals)
    problems = []
    for s in plan.slots:
        got = seen.get(s.block)
        if got is None or got[1] != s.model_index:
            problems.append(f"{s.block}: expected model {s.model_index} {s.model!r}, got {got[1] if got else 'nothing'}")
            continue
        if not got[0]:
            problems.append(f"{s.block}: expected on")
        for k in s.knobs:
            if k.origin == "default":
                continue
            try:
                back = float(got[2][k.name])
            except (KeyError, ValueError):
                back = float("nan")
            if not abs(back - k.value) <= 0.5:
                problems.append(f"{s.block} {k.name}: expected {k.value:g}, got {got[2].get(k.name)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research", required=True, type=Path)
    ap.add_argument("--plan", type=Path, help="write the plan JSON here (default: stdout)")
    ap.add_argument("--eq-gains", help="10 comma-separated dB values for Normal EQ 10 (31 Hz..16 kHz), capped ±6")
    ap.add_argument("--apply", nargs=2, metavar=("PRESET", "NAME"), help="push the plan into PRESET (1..160) and save it as NAME")
    ap.add_argument("--overwrite", action="store_true", help="allow --apply on a preset that already has a name")
    ap.add_argument("--mk300", default="mk300", help='mk300 command (default: mk300 on PATH; e.g. "python3 -m mk300")')
    a = ap.parse_args(argv)
    runner = Runner()
    runner.exe = a.mk300
    gains = [float(x) for x in a.eq_gains.split(",")] if a.eq_gains else None
    try:
        plan = build_plan(load_research(a.research), runner, gains)
    except BuildError as e:
        print("ABORT", e, file=sys.stderr)
        return 2
    if a.plan:
        a.plan.write_text(plan.to_json())
        print(f"plan -> {a.plan}")
    else:
        print(plan.to_json())
    if plan.unmapped:
        print("unmapped params (ignored):", ", ".join(plan.unmapped), file=sys.stderr)
    if plan.unverified:
        print("unverified params (defaults/guesses):", ", ".join(plan.unverified), file=sys.stderr)
    if a.apply:
        preset, name = a.apply
        apply_plan(plan, preset, name, runner, a.overwrite)
        problems = verify_plan(plan, preset, runner)
        if problems:
            print("VERIFY FAILED\n" + "\n".join(problems), file=sys.stderr)
            return 4
        print(f"applied and verified preset {preset} {name!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
