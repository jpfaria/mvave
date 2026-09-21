import pytest

from mvave.bridge import drivers
from mvave.bridge.drivers import hd8, mac


class FakeClient:
    def __init__(self):
        self.valores = {"global/mainOutVolume": 0.5, "global/mute": 0.0}
        self.scenes = ["A.scene", "B.scene"]
        self.carregou = None

    def get(self, path):
        return self.valores[path]

    def set_raw(self, path, v):
        self.valores[path] = v

    def set(self, path, v):
        self.valores[path] = float(v)

    def load_scene(self, nome, keep_gains=False):
        self.carregou = (nome, keep_gains)


def test_hd8_write_is_clamped_and_read_back():
    d = hd8.HD8(client=FakeClient())
    d.write("global/mainOutVolume", 2.0)
    assert d.read("global/mainOutVolume") == 1.0
    d.write("global/mainOutVolume", -1)
    assert d.read("global/mainOutVolume") == 0.0


def test_hd8_toggle_flips_and_reports():
    d = hd8.HD8(client=FakeClient())
    assert d.toggle("global/mute") is True
    assert d.read("global/mute") == 1.0
    assert d.toggle("global/mute") is False


def test_hd8_scenes_lose_the_extension_and_keep_gains():
    c = FakeClient()
    d = hd8.HD8(client=c)
    assert d.scenes() == ["A", "B"]
    assert d.load_scene(1) == "B"
    assert c.carregou == ("B", True)


def test_hd8_refuses_a_scene_that_does_not_exist():
    d = hd8.HD8(client=FakeClient())
    with pytest.raises(drivers.Unsupported):
        d.load_scene(9)


def test_mac_says_why_when_the_output_has_no_system_volume(monkeypatch):
    monkeypatch.setattr(mac, "_osascript", lambda script: "missing value")
    with pytest.raises(drivers.Unsupported) as e:
        mac.MacVolume().read()
    assert "interface de audio" in str(e.value)


def test_unknown_driver_is_refused():
    with pytest.raises(SystemExit):
        drivers.build("nope")
