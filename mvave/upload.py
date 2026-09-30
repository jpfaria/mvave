"""NAM (A2-Lite) and IR upload to the MK-300 (firmware V73), as M-EFCS 3.9.2317 does it.

Decoded from docs/captures/upload-2026-09-29/ (issue #1); the layout is in docs/protocol.md
"Uploads".  Everything here is reproduced byte for byte by
tests/test_upload.py from the same input files M-EFCS imported.

Flow (both kinds): the blob goes to a staging buffer in 1015-byte flagged frames (space 0,
field = byte offset), each acked by the pedal.
  audition: write_u8 space 0xA field 0 = 1 (NAM) / 2 (CAB)  -> the pedal plays the staged blob
  save NAM: the whole blob again with the user name, then write_u8 space 0xF field slot-1 = 0
  save CAB: only the 20-byte header (magic + name + 2 bytes) again, then space 0xF field 256+slot-1 = 0

Every header byte has a known source in M-EFCS (decompiled from the Android build, Dart AOT):
the NAM header constants are hard-coded in nam_a2_lite_exporter.dart `_writeHeader`, the CAB
header is `_cabHeader(name, level)` in import_cab.dart (a 1, then the "CAB Level" slider,
default 50).
"""
from __future__ import annotations

import hashlib
import math
import plistlib
import struct
from dataclasses import dataclass
from pathlib import Path

from . import protocol as p

CHUNK = 1015                 # payload bytes per bulk frame (SUB 70 7E)
SPACE_STAGE = 0x0            # bulk frames: same space number as the preset bank, flagged CMD
SPACE_AUDITION = 0xA
SPACE_SAVE = 0xF
KIND_NAM, KIND_CAB = 1, 2    # value written to SPACE_AUDITION
NAME_LEN = 14                # field size; 13 chars + NUL ("marshall_supe" in AMP 120)
SLOTS = {"AMP": (0, 120), "CAB": (256, 100)}   # save field = base + slot - 1

# Constants of M-EFCS's NamA2LiteExporter._writeHeader (meaning not named in the app).
NAM_HEADER_BYTES = bytes([100, 150, 80, 40, 0, 0])
NAM_HEADER_FLOATS = (150.0, -20.0, 20.0, 425.0, -15.0, 15.0, 1800.0, -10.0, 10.0)
CAB_LEVEL_DEFAULT = 50       # M-EFCS "CAB Level" slider initial value

# sha256 of the input files whose upload was captured (test fixtures).
CAPTURED_INPUTS = {
    "8a1a65511ba65c67904163c095066a6c89897deea3ea112c50a2dd03224091c7": "high_4_a2.nam (AMP 119 BJA_high_4)",
    "5a11ad025543770d93152161c50380afcc26cb7729b96af69f90bd3561056981": "V30_ev_mix_b.wav (CAB 100 V30_ev_mix_b)",
}

IR_RATE = 44100              # the pedal's IR rate: 48 kHz input is resampled to 44.1 kHz
IR_LEN = 2048
_KAISER_BETA = 8.6
_KAISER_HALF = 24


class UnsupportedModel(ValueError):
    pass


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- frames --------------------------------------------------------------------------

def _flagged(cmd: int) -> int:
    return cmd | p.FLAG_UPLOAD


def data_frames(blob: bytes) -> list[bytes]:
    out = []
    for off in range(0, len(blob), CHUNK):
        chunk = blob[off:off + CHUNK]
        out.append(p.build(p.CLS_WRITE, _flagged(p.CMD_READ + 8 * len(chunk)), off, len(chunk), SPACE_STAGE, chunk))
    return out


def audition_frame(kind: int) -> bytes:
    return p.build(p.CLS_WRITE, _flagged(p.CMD_WRITE_U8), 0, 1, SPACE_AUDITION, bytes([kind]))


def save_frame(block: str, slot: int) -> bytes:
    return p.build(p.CLS_WRITE, _flagged(p.CMD_WRITE_U8), slot_field(block, slot), 1, SPACE_SAVE, b"\x00")


def slot_field(block: str, slot: int) -> int:
    base, n = SLOTS[block]
    if not 1 <= slot <= n:
        raise ValueError(f"{block} slot must be 1..{n}, got {slot}")
    return base + slot - 1


def name_field(name: str) -> bytes:
    b = name.encode("ascii")
    if len(b) > NAME_LEN - 1:
        raise ValueError(f"name {name!r} longer than {NAME_LEN - 1} characters")
    return b.ljust(NAME_LEN, b"\0")


# --- NAM (A2-Lite) -------------------------------------------------------------------

# The one architecture the capture proves (TONE3000 "A2", submodel 0 = the Lite one).
_A2_LITE = {
    "channels": 3, "bottleneck": 3, "input_size": 1, "condition_size": 1,
    "kernel_sizes": [6] * 14 + [15, 15] + [6] * 7,
    "dilations": [1, 3, 7, 17, 41, 101, 239] * 2 + [1, 13] + [1, 3, 7, 17, 41, 101, 239],
    "head": {"out_channels": 1, "kernel_size": 16, "bias": True},
}
_A2_LITE_WEIGHTS = 1871


def a2_lite_submodel(model: dict) -> dict:
    """The A2-Lite WaveNet inside an A2 .nam (SlimmableContainer), checked against the
    architecture the capture proves; anything else raises UnsupportedModel."""
    try:
        subs = model["config"]["submodels"]
        sm = subs[0]["model"]
        cfg = sm["config"]
        (la,) = cfg["layers"]
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise UnsupportedModel(f"not an A2 .nam (SlimmableContainer with a WaveNet submodel): {e}") from None
    if model.get("architecture") != "SlimmableContainer" or sm.get("architecture") != "WaveNet":
        raise UnsupportedModel("not an A2 .nam")
    for k, v in _A2_LITE.items():
        if la.get(k) != v:
            raise UnsupportedModel(f"A2-Lite layer {k} = {la.get(k)!r}, expected {v!r}")
    acts = la.get("activation")
    if acts != [{"type": "LeakyReLU", "negative_slope": 0.01}] * 23:
        raise UnsupportedModel("activations are not 23 x LeakyReLU(0.01)")
    if la.get("gating_mode") != ["none"] * 23 or not la.get("layer1x1", {}).get("active") \
            or la.get("head1x1", {}).get("active"):
        raise UnsupportedModel("gating / layer1x1 / head1x1 differ from A2-Lite")
    for k, v in la.items():
        if k.endswith("_film") and v.get("active"):
            raise UnsupportedModel(f"{k} is active")
    if len(sm["weights"]) != _A2_LITE_WEIGHTS:
        raise UnsupportedModel(f"{len(sm['weights'])} weights, expected {_A2_LITE_WEIGHTS}")
    return sm


def _split(sm: dict) -> dict:
    """Weights in NAM's WaveNet order: rechannel, per layer (conv W[out][in][k], conv b,
    input mixin, 1x1 W[out][in], 1x1 b), head W[out][in][k], head b, head_scale."""
    la = sm["config"]["layers"][0]
    w = sm["weights"]
    C, B = la["channels"], la["bottleneck"]
    i = 0

    def take(n):
        nonlocal i
        r = list(range(i, i + n))
        i += n
        return r

    P = {"rechannel": take(C), "layers": []}
    for k in la["kernel_sizes"]:
        P["layers"].append({"k": k, "conv_w": take(B * C * k), "conv_b": take(B), "mix": take(B),
                            "l1": take(C * B), "l1_b": take(C)})
    hk = la["head"]["kernel_size"]
    P["head_w"] = take(B * hk)
    P["tail"] = take(2)          # head bias, head_scale
    assert i == len(w)
    P["hk"] = hk
    return P


def nam_weight_order(sm: dict) -> list[int]:
    """JSON weight index for every float32 slot of the blob (M-EFCS _permuteWeights):
    conv kernels tap-major ([k][in][out]), 1x1 transposed ([in][out]), head [k][in]."""
    P = _split(sm)
    C = B = 3
    idx = list(P["rechannel"])
    for L in P["layers"]:
        k, cw = L["k"], L["conv_w"]
        idx += [cw[o * C * k + j * k + t] for t in range(k) for j in range(C) for o in range(B)]
        idx += L["conv_b"] + L["mix"]
        idx += [L["l1"][o * B + j] for j in range(B) for o in range(C)]
        idx += L["l1_b"]
    hk = P["hk"]
    idx += [P["head_w"][j * hk + t] for t in range(hk) for j in range(B)]
    idx += P["tail"]
    return idx


def _f32(v: float) -> float:
    return struct.unpack("<f", struct.pack("<f", v))[0]


def nam_steady_state(sm: dict) -> list[float]:
    """The 69 trailer floats (after "BEND"): the network's fixed point for zero input, as
    M-EFCS _simulateSteadyState computes it -- residual after layers 0..21 (3 x 22) and the
    summed layer activations that feed the head (3).  Arithmetic in double with the weights
    rounded to float32 and float32 rounding at exactly these points (bit-exact vs. capture)."""
    P = _split(sm)
    w = [_f32(v) for v in sm["weights"]]
    x = [0.0] * 3
    head = [0.0] * 3
    out: list[float] = []
    for n, L in enumerate(P["layers"]):
        k = L["k"]
        z = []
        for o in range(3):
            acc = w[L["conv_b"][o]]
            for t in range(k):
                d = 0.0
                for c in range(3):
                    d += w[L["conv_w"][o * 3 * k + c * k + t]] * x[c]
                acc = _f32(acc + d)
            z.append(acc)
        a = [_f32(v if v > 0 else v * 0.01) for v in z]
        head = [_f32(h + ai) for h, ai in zip(head, a)]
        nx = []
        for o in range(3):
            s = w[L["l1_b"][o]]
            for j in range(3):
                s += w[L["l1"][o * 3 + j]] * a[j]
            nx.append(_f32(x[o] + s))
        x = nx
        if n < len(P["layers"]) - 1:
            out += x
    return out + head


def nam_blob(model: dict, name: str) -> bytes:
    sm = a2_lite_submodel(model)
    w = sm["weights"]
    body = struct.pack(f"<{_A2_LITE_WEIGHTS}f", *(w[i] for i in nam_weight_order(sm)))
    trailer = struct.pack("<69f", *nam_steady_state(sm))
    return (b"NAM\0" + name_field(name) + NAM_HEADER_BYTES
            + struct.pack("<9f", *NAM_HEADER_FLOATS) + body + b"BEND" + bytes(12) + trailer)


def nam_frames(model: dict, slot: int | None, name: str | None = None, audition_name: str = "") -> list[bytes]:
    """M-EFCS's sequence: audition (blob named after the file stem), then, with a slot,
    the save (blob again with `name`)."""
    frames = data_frames(nam_blob(model, audition_name)) + [audition_frame(KIND_NAM)]
    if slot is not None:
        frames += data_frames(nam_blob(model, name or audition_name)) + [save_frame("AMP", slot)]
    return frames


# --- IR ------------------------------------------------------------------------------

@dataclass
class Wav:
    samples: list[int]   # mono, 24-bit integers
    rate: int


def read_wav(path) -> Wav:
    """PCM 16/24/32-bit or float 32/64 WAV (also WAVE_FORMAT_EXTENSIBLE) -> mono int24.
    Float is scaled by 2^23 and rounded, several channels are averaged (our choice, not
    M-EFCS's: the app only accepts 24-bit int files)."""
    b = Path(path).read_bytes()
    if b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        raise ValueError(f"{path}: not a RIFF/WAVE file")
    i, fmt, data = 12, None, None
    while i + 8 <= len(b):
        cid, n = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"fmt ":
            fmt = b[i + 8:i + 8 + n]
        elif cid == b"data":
            data = b[i + 8:i + 8 + n]
        i += 8 + n + (n & 1)
    if fmt is None or data is None:
        raise ValueError(f"{path}: no fmt/data chunk")
    tag, ch, rate, _, blk, bits = struct.unpack("<HHIIHH", fmt[:16])
    if tag == 0xFFFE:
        tag = struct.unpack("<H", fmt[24:26])[0]
    width = bits // 8
    frames = len(data) // blk
    vals: list[float] = []
    for f in range(frames):
        acc = 0.0
        for c in range(ch):
            o = f * blk + c * width
            s = data[o:o + width]
            if tag == 1:
                if width in (2, 3, 4):
                    v = int.from_bytes(s, "little", signed=True) * 2.0 ** (24 - bits)
                else:
                    raise ValueError(f"{path}: {bits}-bit PCM not supported")
            elif tag == 3 and width in (4, 8):
                v = struct.unpack("<f" if width == 4 else "<d", s)[0] * 8388608.0
            else:
                raise ValueError(f"{path}: WAV format {tag}/{bits}-bit not supported")
            acc += v
        vals.append(acc / ch)
    return Wav([max(-8388608, min(8388607, int(round(v)))) for v in vals], rate)


def ir_to_pedal(samples: list[int], rate: int) -> list[int]:
    """M-EFCS's IR conversion (bit-exact vs. capture for 48 kHz input): windowed-sinc
    resampling to 44.1 kHz (Kaiser beta 8.6, +-24 taps, cutoff 44100/rate, taps normalised
    by the sum of the in-range window), rounded to int24, first 2048 samples.
    Rates other than 48 kHz and IRs shorter than ~2250 samples are unverified."""
    import numpy as np

    x = np.asarray(samples, dtype=np.float64) / 8388608.0
    ratio = rate / IR_RATE
    fc = min(1.0, IR_RATE / rate)
    W = _KAISER_HALF
    n = np.arange(IR_LEN)[:, None]
    t = n * ratio
    ks = np.floor(t) + np.arange(-W, W + 2)[None, :]
    d = t - ks
    a = d / W
    win = np.i0(_KAISER_BETA * np.sqrt(np.clip(1 - a * a, 0, None))) / np.i0(_KAISER_BETA)
    h = np.where(np.abs(d) < W, np.sinc(fc * d) * win, 0.0)
    ki = ks.astype(int)
    valid = (ki >= 0) & (ki < len(x))
    num = (np.where(valid, x[np.clip(ki, 0, max(len(x) - 1, 0))] if len(x) else 0.0, 0.0) * h).sum(1)
    den = (h * valid).sum(1)
    y = np.divide(num, den, out=np.zeros_like(num), where=den != 0)
    q = np.clip(np.round(y * 8388608), -8388608, 8388607).astype(int)
    return [int(v) for v in q]


def int24_bytes(samples: list[int]) -> bytes:
    return b"".join((v & 0xFFFFFF).to_bytes(3, "little") for v in samples)


def cab_header(name: str, level: int = CAB_LEVEL_DEFAULT) -> bytes:
    if not 0 <= level <= 100:
        raise ValueError(f"CAB level must be 0..100, got {level}")
    return b"CAB\0" + name_field(name) + bytes([1, level])


def cab_blob(pcm: list[int], name: str = "", level: int = CAB_LEVEL_DEFAULT) -> bytes:
    return cab_header(name, level) + int24_bytes(pcm)


def cab_frames(samples: list[int], rate: int, slot: int | None, name: str = "",
               level: int = CAB_LEVEL_DEFAULT) -> list[bytes]:
    """M-EFCS's sequence: audition (blob with an empty name), then, with a slot, the
    20-byte header with `name` and the save to CAB `slot`."""
    frames = data_frames(cab_blob(ir_to_pedal(samples, rate), level=level)) + [audition_frame(KIND_CAB)]
    if slot is not None:
        hdr = cab_header(name, level)
        frames += [p.build(p.CLS_WRITE, _flagged(p.CMD_READ + 8 * len(hdr)), 0, len(hdr), SPACE_STAGE, hdr),
                   save_frame("CAB", slot)]
    return frames


# --- capture reader ------------------------------------------------------------------

def read_mmon(path):
    """(timestamp_ns, host_to_pedal, frame) for every SysEx in a MIDI Monitor document."""
    a = plistlib.loads(plistlib.load(open(path, "rb"))["messageData"])
    o = a["$objects"]
    for ref in o[1]["NS.objects"]:
        m = o[ref.data]
        if "data" not in m or "originatingEndpoint" not in m:
            continue
        yield m["timeStampInNanos"], str(o[m["originatingEndpoint"].data]).startswith("To"), \
            b"\xf0" + o[m["data"].data] + b"\xf7"


def send(dev, frames: list[bytes], timeout: float = 5.0, progress=None) -> None:
    """Send each frame and wait for its ack (MVave.write), like M-EFCS does."""
    for i, f in enumerate(frames):
        dev.write(f, timeout=timeout)
        if progress:
            progress(i + 1, len(frames))
