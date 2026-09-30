from mvave import catalog as catalog_mod
from mvave.resolve import resolve as _resolve

cat = catalog_mod.load()


def resolve(block, q):
    return _resolve(cat, block, q)


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


def test_resolve_alias_with_separator():
    # 'bluesbreaker' -> 'blues_od': an alias written with '_' must match the model name 1BLUES_OD
    assert resolve("DS", "Bluesbreaker")[0][0]["name"] == "1BLUES_OD"
    assert resolve("DS", "Marshall Bluesbreaker")[0][0]["name"] == "1BLUES_OD"


def test_user_imports_29_09():
    """Since V73 AMP 1-120 / CAB 1-100 take user NAM A2 / IR imports (issue #1)."""
    assert cat.user_import("AMP", 118)["name"] == "BJA_high_4" and cat.user_import("AMP", 118)["kind"] == "NAM"
    assert cat.user_import("AMP", 119)["name"] == "marshall_supe"
    assert cat.user_import("CAB", 99)["name"] == "V30_ev_mix_b" and cat.user_import("CAB", 99)["kind"] == "IR"
    assert cat.user_import("AMP", 0) is None
    assert cat.label("AMP", 118).startswith("BJA_high_4")
    assert cat.label("AMP", 52) == "53J900_CH1"
    assert cat.find_model("AMP", "BJA_high_4")["index"] == 118
    assert cat.find_model("CAB", "V30_ev_mix_b")["index"] == 99
    assert cat.importable("AMP") == (1, 120) and cat.importable("CAB") == (1, 100) and cat.importable("DS") is None
