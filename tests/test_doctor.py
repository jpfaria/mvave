import pytest

from mvave import cli
from mvave import doctor as D
from mvave.devices import mk300


def test_diagnose_flags_usb_audio_not_on():
    g = bytearray(86)
    g[mk300.PROFILE.usb_audio_field] = 2  # RESAMPLE
    problems = D.diagnose(mk300.PROFILE, bytes(g))
    assert len(problems) == 1
    assert "usb-audio" in problems[0] and "RESAMPLE" in problems[0]
    assert "mvave global-set usb-audio 0" in problems[0]


def test_diagnose_clean_when_usb_audio_on():
    g = bytearray(86)  # byte 0x3D defaults to 0 == ON
    assert D.diagnose(mk300.PROFILE, bytes(g)) == []


class FakeConnectedDev:
    """Stands in for the `with _dev(a) as d:` context in cli.py — never opens a MIDI port."""

    def __init__(self, g):
        self.g = g

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read_global(self):
        return bytes(self.g)


def test_cmd_doctor_exits_1_and_prints_fix_when_dirty(monkeypatch, capsys):
    g = bytearray(86)
    g[cli.PROF.usb_audio_field] = 2
    monkeypatch.setattr(cli, "_dev", lambda a: FakeConnectedDev(g))
    with pytest.raises(SystemExit) as exc:
        cli.main(["doctor"])
    assert exc.value.code == 1
    assert "mvave global-set usb-audio 0" in capsys.readouterr().err


def test_cmd_doctor_exits_0_when_clean(monkeypatch, capsys):
    g = bytearray(86)
    monkeypatch.setattr(cli, "_dev", lambda a: FakeConnectedDev(g))
    assert cli.main(["doctor"]) == 0
