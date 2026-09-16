from mk300 import catalog as cat
from mk300.resolve import resolve


def test_counts():
    assert {b: len(cat.models(b)) for b in cat.block_names()} == {
        "WAH": 6, "FX": 16, "GATE": 8, "DS": 40, "AMP": 120, "CAB": 100, "EQ": 3, "MOD": 20, "DLY": 27, "REV": 18, "VOL": 1}


def test_indices_match_factory_presets():
    # JM-CL (factory [001]) uses FX 8 Compress, DS 32 33MID-BOST, AMP 52 53J900_CH1, CAB 2 3JVM_G12_ECM, REV 10 Hall stereo
    assert cat.model("FX", 8)["name"] == "Compress"
    assert cat.model("DS", 32)["name"] == "33MID-BOST"
    assert cat.model("AMP", 52)["name"] == "53J900_CH1"
    assert cat.model("CAB", 2)["name"] == "3JVM_G12_ECM"
    assert cat.model("REV", 10)["name"] == "Hall stereo"


def test_find_and_knobs():
    assert cat.find_model("AMP", "53")["index"] == 52
    assert cat.find_model("DLY", "analog stereo")["index"] == 17
    assert cat.knob_names("FX", 8) == ["Sustain", "Attack", "Level", "Blend"]
    assert cat.knob_index("AMP", 0, "gain") == 0 and cat.knob_index("AMP", 0, "pres") == 6


def test_resolve():
    names = [m["name"] for m, _ in resolve("AMP", "Marshall JCM800")[:6]]
    assert any("J800" in n for n in names)
    assert resolve("DS", "Ibanez TS808")[0][0]["name"] == "2TS8"
    assert resolve("CAB", "Vox AC30")[0][0]["name"].startswith("17VOX_AC30")
