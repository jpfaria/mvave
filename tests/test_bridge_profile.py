import pytest

from mvave.bridge import profile


PERFIL = {
    "surface": "smc-mixer",
    "banks": [
        {"name": "HD 8",
         "faders": {1: {"driver": "hd8", "target": "global/mainOutVolume",
                        "label": "MAIN", "group": "out", "mute": "global/mute"},
                    5: {"driver": "hd8", "target": "line/ch1/volume",
                        "label": "GUITA 1", "group": "in"}},
         "buttons": {"rec": "scene", "select": "bank"}},
        {"name": "Mac", "faders": {1: {"driver": "mac"}}},
    ],
}


def test_parses_banks_faders_and_buttons():
    p = profile.parse_profile(PERFIL)
    assert [b.name for b in p.banks] == ["HD 8", "Mac"]
    main = p.banks[0].faders[1]
    assert (main.driver, main.label, main.group, main.mute) == \
        ("hd8", "MAIN", "out", "global/mute")
    assert p.banks[0].buttons["rec"] == "scene"


def test_label_falls_back_to_the_target():
    p = profile.parse_profile({"banks": [{"faders": {2: {"driver": "hd8",
                                                        "target": "aux/ch10/volume"}}}]})
    assert p.banks[0].faders[2].label == "aux/ch10/volume"


def test_bank_index_wraps_around():
    p = profile.parse_profile(PERFIL)
    assert p.bank(2).name == "HD 8" and p.bank(-1).name == "Mac"


def test_a_destination_without_driver_is_refused():
    with pytest.raises(SystemExit):
        profile.parse_profile({"banks": [{"faders": {1: {"target": "x"}}}]})


def test_a_profile_without_banks_is_refused():
    with pytest.raises(SystemExit):
        profile.parse_profile({})


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        profile.load_profile(tmp_path / "nao-existe.yaml")
