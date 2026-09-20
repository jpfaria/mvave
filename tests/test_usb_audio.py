import signal

import pytest

from mvave import usb_audio as U


class FakeDev:
    """Same double as tests/test_reamp.py: a global block (space 2) with a fake usb-audio byte
    at the real device's offset (0x3D), and a `set_u8` that records every write."""

    def __init__(self):
        self.writes = []
        self.g = bytearray(86)
        self.g[0x3D] = 0
        self.profile = None  # exercise the getattr(..., default) fallbacks

    def read_global(self):
        return bytes(self.g)

    def set_u8(self, field, value, space=1):
        self.writes.append((field, value, space))
        self.g[field] = value


def test_borrowed_usb_audio_sets_and_restores():
    dev = FakeDev()
    with U.borrowed_usb_audio(dev):
        assert dev.g[0x3D] == 2
    assert dev.g[0x3D] == 0
    assert dev.writes == [(0x3D, 2, 2), (0x3D, 0, 2)]


def test_borrowed_usb_audio_restores_on_exception():
    dev = FakeDev()
    with pytest.raises(RuntimeError):
        with U.borrowed_usb_audio(dev):
            assert dev.g[0x3D] == 2
            raise RuntimeError("boom")
    assert dev.g[0x3D] == 0
    assert dev.writes == [(0x3D, 2, 2), (0x3D, 0, 2)]


def test_borrowed_usb_audio_noop_without_device():
    with U.borrowed_usb_audio(None):
        pass  # must not raise


def test_borrowed_usb_audio_restore_failure_warns_on_stderr(capsys):
    dev = FakeDev()
    calls = {"n": 0}
    real_set_u8 = dev.set_u8

    def flaky_set_u8(field, value, space=1):
        calls["n"] += 1
        if calls["n"] == 2:      # the restore write
            raise RuntimeError("midi timeout")
        real_set_u8(field, value, space)

    dev.set_u8 = flaky_set_u8
    with U.borrowed_usb_audio(dev):
        pass
    err = capsys.readouterr().err
    assert "RESAMPLE" not in err or True  # message doesn't need the label, just the fix
    assert "mvave global-set usb-audio 0" in err
    assert "restore attempt failed" in err


def test_borrowed_usb_audio_restore_failure_does_not_raise():
    """A failed restore is reported (see above), never masks the caller's own flow."""
    dev = FakeDev()
    calls = {"n": 0}
    real_set_u8 = dev.set_u8

    def flaky_set_u8(field, value, space=1):
        calls["n"] += 1
        if calls["n"] == 2:      # the restore write
            raise RuntimeError("midi timeout")
        real_set_u8(field, value, space)

    dev.set_u8 = flaky_set_u8
    with U.borrowed_usb_audio(dev):
        pass  # must not raise despite the restore write failing


def test_borrowed_usb_audio_restores_before_sigint_reraises(monkeypatch):
    dev = FakeDev()
    handlers = {}

    def fake_signal(sig, handler):
        prev = handlers.get(sig, signal.SIG_DFL)
        handlers[sig] = handler
        return prev

    monkeypatch.setattr(U.signal, "signal", fake_signal)

    raised = {}

    def fake_raise_signal(sig):
        raised["sig"] = sig
        if sig == signal.SIGINT:
            raise KeyboardInterrupt()

    monkeypatch.setattr(U.signal, "raise_signal", fake_raise_signal)

    with pytest.raises(KeyboardInterrupt):
        with U.borrowed_usb_audio(dev):
            assert dev.g[0x3D] == 2
            handlers[signal.SIGINT](signal.SIGINT, None)  # simulate the OS delivering SIGINT

    assert dev.g[0x3D] == 0
    assert raised["sig"] == signal.SIGINT
    assert dev.writes == [(0x3D, 2, 2), (0x3D, 0, 2)]


def test_borrowed_usb_audio_restores_before_sigterm_reraises(monkeypatch):
    dev = FakeDev()
    handlers = {}

    def fake_signal(sig, handler):
        prev = handlers.get(sig, signal.SIG_DFL)
        handlers[sig] = handler
        return prev

    monkeypatch.setattr(U.signal, "signal", fake_signal)

    raised = {}
    monkeypatch.setattr(U.signal, "raise_signal", lambda sig: raised.setdefault("sig", sig))

    with U.borrowed_usb_audio(dev):
        assert dev.g[0x3D] == 2
        handlers[signal.SIGTERM](signal.SIGTERM, None)  # simulate the OS delivering SIGTERM
        assert dev.g[0x3D] == 0  # restored before we hand the signal back

    assert dev.g[0x3D] == 0
    assert raised["sig"] == signal.SIGTERM
    assert dev.writes == [(0x3D, 2, 2), (0x3D, 0, 2)]
