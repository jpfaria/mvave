"""Play a DI through the pedal and record the result over its USB audio interface.

The MK-300 is a 2-in/2-out 44.1 kHz USB audio device (CoreMIDI/CoreAudio name `USB-Audio`).
With the global USB Audio field (space 2, offset 0x3D) set to RESAMPLE (2), USB playback is
routed into the effect chain and the processed signal comes back on the USB input (measured
2026-09-16: a -20 dBFS sine returned at -26 dBFS through the JM-CL preset; DRY mode returns
silence). The field is restored afterwards. Needs the `reamp` extra: pip install "mvave[reamp]".
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from .usb_audio import borrowed_usb_audio

DEVICE = "USB-Audio"
DEVICE_RATE = 44100
CHANNELS = 2
BLOCK = 2048
SILENCE_DBFS = -60.0


class NoSignal(RuntimeError):
    pass


@dataclass(frozen=True)
class ReampResult:
    frames: int
    rms_db: float


def _load_mono_44k(path: Path) -> np.ndarray:
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != DEVICE_RATE:
        n = int(round(len(mono) * DEVICE_RATE / rate))
        mono = np.interp(np.linspace(0, len(mono) - 1, n), np.arange(len(mono)), mono).astype(np.float32)
    return mono


def _find_device(name: str):
    import sounddevice as sd
    devs = sd.query_devices()
    ins = [i for i, d in enumerate(devs) if d["name"] == name and d["max_input_channels"] >= CHANNELS]
    outs = [i for i, d in enumerate(devs) if d["name"] == name and d["max_output_channels"] >= CHANNELS]
    if not ins or not outs:
        raise RuntimeError(f"USB audio device {name!r} not found (is the pedal on USB?)")
    return ins[0], outs[0]


def _default_playrec(play: np.ndarray, device_name: str) -> np.ndarray:
    import sounddevice as sd
    din, dout = _find_device(device_name)
    rec = sd.playrec(play, samplerate=DEVICE_RATE, channels=CHANNELS, device=(din, dout), dtype="float32", blocksize=BLOCK)
    sd.wait()
    return np.asarray(rec)


def reamp(di, out, *, tail_s: float = 2.0, mono: bool = False, device=None,
          device_name: str | None = None, playrec=None) -> ReampResult:
    """`device` is an mvave.device.MVave (its usb-audio field is borrowed for the run via
    mvave.usb_audio.borrowed_usb_audio, which guarantees it is restored — see that module for
    why this must never be done any other way); None = leave the global alone. `playrec(play,
    device_name) -> recorded` is injectable."""
    playrec = playrec or _default_playrec
    prof = getattr(device, "profile", None)
    device_name = device_name or getattr(prof, "audio_device", DEVICE)
    di_signal = _load_mono_44k(Path(di))
    total = len(di_signal) + int(tail_s * DEVICE_RATE)
    play = np.zeros((total, CHANNELS), np.float32)
    play[: len(di_signal), 0] = di_signal
    play[: len(di_signal), 1] = di_signal
    with borrowed_usb_audio(device):
        rec = playrec(play, device_name)[:total]
    rms = float(np.sqrt(np.mean(rec ** 2)) + 1e-12)
    rms_db = 20 * float(np.log10(rms))
    if rms_db < SILENCE_DBFS:
        raise NoSignal(f"recorded {rms_db:.1f} dBFS: nothing came back through the pedal")
    sf.write(Path(out), rec[:, 0] if mono else rec, DEVICE_RATE, subtype="PCM_24")
    return ReampResult(total, round(rms_db, 1))
