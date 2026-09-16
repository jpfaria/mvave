import sys

import pytest

from scripts import build_patch as B
from test_build_patch import FIX, RealRunner


class RecordingRunner(RealRunner):
    """Real for catalog commands, recorded for pedal commands."""

    def __init__(self, slot_name="USER PRESET 150", read_out=None):
        self.calls, self.slot_name, self.read_out = [], slot_name, read_out

    def run(self, args):
        if args[0] in ("resolve", "params"):
            return super().run(args)
        self.calls.append(list(args))
        if args[0] == "read":
            return 0, self.read_out or f"[150] {self.slot_name}   vol 60  bpm 120  pan +0\n"
        return 0, ""


@pytest.fixture
def plan():
    return B.build_plan(B.load_research(FIX / "gravity_rhythm.json"), RealRunner())


def test_apply_sequence(plan):
    r = RecordingRunner()
    cmds = B.apply_plan(plan, "150", "GRAVITY", r)
    assert cmds[0] == ["read", "150"] and cmds[1] == ["load", "150"]
    assert ["model", "AMP", "60"] in cmds and ["model", "DS", "1"] in cmds
    assert ["param", "DS", "0", "20"] in cmds and ["param", "DLY", "0", "454"] in cmds
    assert ["enable", "AMP", "on"] in cmds and ["enable", "REV", "off"] in cmds and ["enable", "WAH", "off"] in cmds
    assert not any(c[:2] == ["enable", "VOL"] for c in cmds)
    assert ["bpm", "66"] in cmds and cmds[-1] == ["save", "150", "GRAVITY"]
    assert not any(c[0] in ("volume", "pan", "chain", "global-set", "rename", "copy") for c in cmds)
    assert r.calls == cmds


def test_refuses_named_preset_without_overwrite(plan):
    with pytest.raises(SystemExit) as e:
        B.apply_plan(plan, "150", "GRAVITY", RecordingRunner("MY-TONE"))
    assert e.value.code == 5
    cmds = B.apply_plan(plan, "150", "GRAVITY", RecordingRunner("MY-TONE"), overwrite=True)
    assert cmds[-1] == ["save", "150", "GRAVITY", "--overwrite"]


def _read(plan, override=None):
    override = override or {}
    lines = ["[150] GRAVITY   vol 60  bpm 66  pan +0", "chain: WAH > FX > GATE > DS > AMP > CAB > EQ > MOD > REV > DLY > VOL"]
    for s in plan.slots:
        kv = "  ".join(f"{k.name}={override.get((s.block, k.name), int(k.value))}" for k in s.knobs)
        idx = override.get((s.block, "model"), s.model_index)
        lines.append(f"  on  {s.block:<4} {B.BLOCKS.index(s.block):2d}:{idx:<3d} {s.model:<16} {kv}")
    return "\n".join(lines)


def test_verify_reads_back(plan):
    good = _read(plan)
    assert B.verify_plan(plan, "150", RecordingRunner(read_out=good)) == []
    bad = _read(plan, {("AMP", "model"): 3})
    assert any("AMP" in m for m in B.verify_plan(plan, "150", RecordingRunner(read_out=bad)))
    wrong_knob = _read(plan, {("DS", "Gain"): 50})
    assert any("Gain" in m for m in B.verify_plan(plan, "150", RecordingRunner(read_out=wrong_knob)))


def test_main_plan_only_and_exit_codes(tmp_path, monkeypatch):
    out = tmp_path / "plan.json"
    monkeypatch.setattr(B.Runner, "exe", f"{sys.executable} -m mk300")
    monkeypatch.setenv("PYTHONPATH", str(FIX.parents[2]))
    monkeypatch.chdir(FIX.parents[2])
    mk = ["--mk300", f"{sys.executable} -m mk300"]
    assert B.main(["--research", str(FIX / "gravity_rhythm.json"), "--plan", str(out), *mk]) == 0
    assert '"Normal EQ 10"' in out.read_text()
    bad = tmp_path / "bad.json"
    bad.write_text((FIX / "gravity_rhythm.json").read_text().replace("Dumble Overdrive Special", "Kemper"))
    assert B.main(["--research", str(bad), *mk]) == 2
