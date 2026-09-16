import numpy as np
import pytest

sf = pytest.importorskip("soundfile")
from mk300 import reamp as R


class FakeDev:
    def __init__(self):
        self.writes = []
        self.g = bytearray(86); self.g[0x3D] = 0
    def read_global(self):
        return bytes(self.g)
    def set_u8(self, field, value, space=1):
        self.writes.append((field, value, space)); self.g[field] = value


def test_reamp_sets_resample_and_restores(tmp_path):
    di = tmp_path / "di.wav"
    sf.write(di, (0.1 * np.sin(np.linspace(0, 200, 44100))).astype("float32"), 44100)
    dev = FakeDev()
    seen = {}
    def playrec(play, name):
        seen["shape"] = play.shape; seen["mode"] = dev.g[0x3D]
        return play * 0.5
    r = R.reamp(di, tmp_path / "wet.wav", tail_s=1.0, device=dev, playrec=playrec)
    assert seen["mode"] == 2 and dev.g[0x3D] == 0 and dev.writes == [(0x3D, 2, 2), (0x3D, 0, 2)]
    assert seen["shape"] == (44100 * 2, 2) and r.frames == 88200 and r.rms_db < 0
    data, rate = sf.read(tmp_path / "wet.wav")
    assert rate == 44100 and data.shape == (88200, 2)


def test_reamp_no_signal(tmp_path):
    di = tmp_path / "di.wav"
    sf.write(di, np.zeros(4410, "float32"), 44100)
    with pytest.raises(R.NoSignal):
        R.reamp(di, tmp_path / "wet.wav", tail_s=0, playrec=lambda play, name: np.zeros_like(play))
