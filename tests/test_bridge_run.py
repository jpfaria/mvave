import pytest

from mvave.bridge import run


def test_find_port_matches_by_hint():
    assert run.find_port("SMC-Mixer-Master",
                         ["Quantum HD 8 MIDI", "SINCO SMC-Mixer-Master"]) \
        == "SINCO SMC-Mixer-Master"


def test_find_port_without_a_match_is_refused():
    with pytest.raises(SystemExit) as e:
        run.find_port("SMC-Mixer-Master", ["Quantum HD 8 MIDI"])
    assert "nenhuma porta" in str(e.value)
