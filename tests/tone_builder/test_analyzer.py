import shutil
from pathlib import Path

from scripts import analyzer as A

FIX = Path(__file__).parent / "fixtures"


def fake_run(dest_name, seen=None):
    def run(args, out_dir):
        if seen is not None:
            seen.append(args)
        shutil.copy(FIX / dest_name, Path(out_dir) / dest_name)
        return 0, ""
    return run


def test_fingerprint_reads_floor_and_degraded(tmp_path):
    fp = A.fingerprint("ref.wav", tmp_path, run=fake_run("fingerprint.json"))
    assert fp["self_floor_pct"] == 89.0 and fp["degraded"] is False


def test_compare_and_within(tmp_path):
    d = A.compare("ref.wav", "wet.wav", tmp_path, run=fake_run("diff.json"))
    assert d["proximity_pct"] == 84.2 and A.within(84.2, 89.0) is False and A.within(86.5, 89.0) is True


def test_eq_match_maps_10_bands_to_8_and_back(tmp_path):
    seen = []
    current = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]                # one value per Graphic EQ band
    gains = A.eq_match("ref.wav", "wet.wav", current, out_dir=tmp_path, run=fake_run("eq_match.json", seen))
    assert seen[0][:3] == ["eq-match", "ref.wav", "wet.wav"]
    assert seen[0][seen[0].index("--gains") + 1] == "1,2,3,4,5,6,7,8"      # 80Hz<-63Hz ... 10240Hz<-8kHz
    assert "--bands" not in seen[0]
    # new_gains [1,2,-1,0,3,-8,2,1] at 80..10240 -> 31 & 63 take 80's, 16k takes 10240's, -8 capped to -6
    assert gains == [1, 1, 2, -1, 0, 3, -6, 2, 1, 1]


def test_command_lines(tmp_path):
    seen = []
    A.compare("r.wav", "w.wav", tmp_path, run=fake_run("diff.json", seen))
    assert seen[0][:3] == ["compare", "r.wav", "w.wav"] and "--out-dir" in seen[0]
