from mk300 import preset as pr


def test_factory_jm_od_layout():
    # The [002] JM-OD record captured from the pedal on 2026-09-16 (docs/captures) matches the
    # editor's factory bank; a few fields checked against what the editor displayed.
    raw = bytes.fromhex(open("tests/fixtures/jm-od.hex").read())
    p = pr.Preset(raw)
    assert p.name == "JM-OD"
    assert p.volume == 60 and p.bpm == 179 and p.pan == 0
    assert p.chain == [0, 1, 2, 3, 4, 5, 6, 7, 9, 8, 10]
    assert [p.enabled(b) for b in range(11)] == [False, False, False, False, True, True, False, False, True, True, True]
    assert p.model(pr.BLOCK_ID["AMP"]) == 0x35 and p.model(pr.BLOCK_ID["REV"]) == 10
    assert p.knobs(pr.BLOCK_ID["WAH"])[:3] == [50, 50, 50]
    assert p.knobs(pr.BLOCK_ID["FX"])[:5] == [20, 88, 50, 100, 50]


def test_offsets():
    assert pr.knob_offset(0, 0) == 0x42 and pr.knob_offset(1, 0) == 0x5A
    assert pr.model_offset(1) == 0x37 and pr.enabled_offset(1) == 0x2C
