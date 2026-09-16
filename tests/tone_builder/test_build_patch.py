import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import build_patch as B

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[2]


class RealRunner(B.Runner):
    """The real catalog commands (no pedal): `python3 -m mk300 resolve|params`."""
    exe = f"{sys.executable} -m mk300"

    def run(self, args):
        p = subprocess.run([*shlex.split(self.exe), *args], capture_output=True, text=True,
                           cwd=ROOT, env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})
        return p.returncode, p.stdout + p.stderr


def test_plan_gravity():
    plan = B.build_plan(B.load_research(FIX / "gravity_rhythm.json"), RealRunner())
    by = {s.block: s for s in plan.slots}
    assert [s.block for s in plan.slots] == ["GATE", "DS", "AMP", "CAB", "EQ", "DLY"]
    assert by["DS"].model == "2TS8" and by["AMP"].model == "61DUMBLE_FG" and by["CAB"].model == "10MAR1960_412"
    assert by["DLY"].model == "Analog" and by["EQ"].model == "Normal EQ 10"
    ds = {k.name: k for k in by["DS"].knobs}
    assert ds["Gain"].value == 20 and ds["Gain"].origin == "research" and ds["Level"].value == 60
    dly = {k.name: k for k in by["DLY"].knobs}
    assert dly["Time"].value == 454 and dly["Fb"].value == 28 and dly["Mix"].value == 30
    assert all(k.value == 0 and k.origin == "eq" for k in by["EQ"].knobs)
    assert plan.tempo == 66 and plan.unverified == ["noise gate"]


def test_uncited_and_no_cab_abort():
    r = B.load_research(FIX / "gravity_rhythm.json")
    r["amp"]["sources"] = []
    with pytest.raises(B.BuildError) as e:
        B.build_plan(r, RealRunner())
    assert e.value.reason == "uncited"
    r = B.load_research(FIX / "gravity_rhythm.json")
    r["cab"] = None
    with pytest.raises(B.BuildError) as e:
        B.build_plan(r, RealRunner())
    assert e.value.reason == "no_cab"


def test_unresolved_and_forbidden():
    r = B.load_research(FIX / "gravity_rhythm.json")
    r["amp"]["name"] = "Kemper Profiler"
    with pytest.raises(B.BuildError) as e:
        B.build_plan(r, RealRunner())
    assert e.value.reason == "unresolved"
    r = B.load_research(FIX / "gravity_rhythm.json")
    r["fx"].append({"type": "volume", "name": "vol", "sources": ["https://example.org"]})
    with pytest.raises(B.BuildError) as e:
        B.build_plan(r, RealRunner())
    assert e.value.reason == "forbidden"


def test_second_drive_goes_to_fx_as_boost_and_third_is_too_many():
    r = B.load_research(FIX / "gravity_rhythm.json")
    r["drives"].append({"name": "Xotic EP Booster", "params": {}, "provenance": "sourced", "sources": ["https://example.org"]})
    plan = B.build_plan(r, RealRunner())
    assert {s.block: s.model for s in plan.slots}["FX"].startswith("Boost") or "Boost" in {s.block: s.model for s in plan.slots}["FX"]
    r["drives"].append({"name": "Klon Centaur", "params": {}, "provenance": "sourced", "sources": ["https://example.org"]})
    with pytest.raises(B.BuildError) as e:
        B.build_plan(r, RealRunner())
    assert e.value.reason == "too_many"


def test_eq_gains_capped():
    plan = B.build_plan(B.load_research(FIX / "gravity_rhythm.json"), RealRunner(), eq_gains=[9, -9, 1, 0, 0, 0, 0, 0, 0, 2])
    eq = [k.value for k in next(s for s in plan.slots if s.block == "EQ").knobs]
    assert eq[:3] == [6, -6, 1] and eq[9] == 2
