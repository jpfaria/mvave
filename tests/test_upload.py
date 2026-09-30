"""Acceptance: the upload encoder reproduces, byte for byte, what M-EFCS 3.9.2317 sent to
the MK-300 (firmware V73) on 2026-09-29 (docs/captures/upload-2026-09-29/).

Inputs:
  tests/fixtures/upload/high_4_a2.nam.gz        the .nam file M-EFCS imported (gzip of the original)
  tests/fixtures/upload/V30_ev_mix_b.head2300.wav  first 2300 samples of the IR it imported
      (24-bit / 48 kHz / mono). The pedal keeps 2048 samples at 44.1 kHz, which only
      reads the first ~2254 input samples, so the output is identical to the full file.
"""
import gzip
import io
import json
import math
import struct
import wave
from pathlib import Path

import pytest

from mvave import protocol as p
from mvave import upload as up

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "docs" / "captures" / "upload-2026-09-29"
FIX = Path(__file__).resolve().parent / "fixtures" / "upload"


def host_writes(name):
    """Every host -> pedal frame of the capture except the editor's 1 s read polls."""
    return [f for _, out, f in up.read_mmon(CAP / name) if out and p.parse(f, verify=False).cls != p.CLS_READ]


@pytest.fixture(scope="module")
def nam_model():
    return json.loads(gzip.decompress((FIX / "high_4_a2.nam.gz").read_bytes()))


# --- frame layer -------------------------------------------------------------

def test_captured_upload_frames_verify_with_the_flag_rule():
    for name in ("nam-upload.mmon", "cab-upload.mmon"):
        for f in host_writes(name):
            fr = p.parse(f)               # raises on a bad checksum
            assert fr.cmd & p.FLAG_UPLOAD


def test_flagged_checksum_is_one_below_the_plain_one():
    plain = p.build(p.CLS_WRITE, p.CMD_WRITE_U8, 0, 1, 0xA, b"\x01")
    flagged = p.build(p.CLS_WRITE, p.CMD_WRITE_U8 | p.FLAG_UPLOAD, 0, 1, 0xA, b"\x01")
    assert flagged.hex(" ") == "f0 00 32 09 49 00 00 40 02 00 00 00 00 1a 00 00 00 01 30 01 f7"
    assert p.unpack7(plain[17:-1])[-1] - 1 == p.unpack7(flagged[17:-1])[-1]


# --- NAM ---------------------------------------------------------------------

def test_nam_audition_and_save_match_capture_byte_for_byte(nam_model):
    got = up.nam_frames(nam_model, slot=119, name="BJA_high_4", audition_name="high_4_a2")
    assert got == host_writes("nam-upload.mmon")


def test_nam_audition_only_is_the_first_part(nam_model):
    got = up.nam_frames(nam_model, slot=None, audition_name="high_4_a2")
    assert got == host_writes("nam-upload.mmon")[:9]


def test_nam_blob_layout(nam_model):
    blob = up.nam_blob(nam_model, "BJA_high_4")
    assert len(blob) == 7836
    assert blob[:4] == b"NAM\0" and blob[4:18] == b"BJA_high_4".ljust(14, b"\0")
    assert blob[7544:7548] == b"BEND"


def test_nam_steady_state_trailer_is_derived_not_copied(nam_model):
    """The 69 trailer floats are the zero-input fixed point: residual after layers 0..21
    plus the summed activations (head input). Recomputed, not stored."""
    trailer = up.nam_steady_state(up.a2_lite_submodel(nam_model))
    blob = up.nam_blob(nam_model, "x")
    assert struct.pack("<69f", *trailer) == blob[7560:]


def test_nam_rejects_non_a2(nam_model):
    bad = json.loads(json.dumps(nam_model))
    bad["config"]["submodels"][0]["model"]["config"]["layers"][0]["channels"] = 4
    with pytest.raises(up.UnsupportedModel):
        up.nam_blob(bad, "x")


# --- IR ----------------------------------------------------------------------

def test_ir_resample_matches_capture_all_2048_samples():
    x = up.read_wav(FIX / "V30_ev_mix_b.head2300.wav")
    got = up.ir_to_pedal(x.samples, x.rate)
    cab = b"".join(p.parse(f).payload for f in host_writes("cab-upload.mmon")[:7])
    assert len(got) == 2048
    assert up.int24_bytes(got) == cab[20:]


def test_cab_audition_and_save_match_capture_byte_for_byte():
    x = up.read_wav(FIX / "V30_ev_mix_b.head2300.wav")
    got = up.cab_frames(x.samples, x.rate, slot=100, name="V30_ev_mix_b")
    assert got == host_writes("cab-upload.mmon")


def test_cab_audition_only():
    x = up.read_wav(FIX / "V30_ev_mix_b.head2300.wav")
    got = up.cab_frames(x.samples, x.rate, slot=None, name="")
    assert got == host_writes("cab-upload.mmon")[:8]


def _wav(fmt_tag, bits, ch, rate, frames):
    raw = io.BytesIO()
    data = b"".join(frames)
    blk = ch * bits // 8
    raw.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE")
    raw.write(b"fmt " + struct.pack("<IHHIIHH", 16, fmt_tag, ch, rate, rate * blk, blk, bits))
    raw.write(b"data" + struct.pack("<I", len(data)) + data)
    return raw.getvalue()


def test_read_wav_float32_stereo_becomes_int24_mono(tmp_path):
    f = tmp_path / "f.wav"
    f.write_bytes(_wav(3, 32, 2, 48000, [struct.pack("<ff", 0.5, 0.25), struct.pack("<ff", -1.0, -1.0)]))
    w = up.read_wav(f)
    assert w.rate == 48000
    assert w.samples == [round(0.375 * 8388608), -8388608]


def test_read_wav_int16(tmp_path):
    f = tmp_path / "i.wav"
    f.write_bytes(_wav(1, 16, 1, 48000, [struct.pack("<h", 16384)]))
    assert up.read_wav(f).samples == [16384 << 8]


# --- slots / names -----------------------------------------------------------

@pytest.mark.parametrize("kind,slot,field", [("AMP", 1, 0), ("AMP", 119, 118), ("AMP", 120, 119),
                                             ("CAB", 1, 256), ("CAB", 100, 355)])
def test_slot_fields(kind, slot, field):
    assert up.slot_field(kind, slot) == field


@pytest.mark.parametrize("kind,slot", [("AMP", 0), ("AMP", 121), ("CAB", 0), ("CAB", 101)])
def test_slot_out_of_range(kind, slot):
    with pytest.raises(ValueError):
        up.slot_field(kind, slot)


def test_name_longer_than_13_is_refused():
    with pytest.raises(ValueError):
        up.name_field("marshall_super")
    assert up.name_field("marshall_supe") == b"marshall_supe\0"


def test_cli_dry_run_audition(capsys):
    from mvave import cli
    cli.main(["upload", "ir", str(FIX / "V30_ev_mix_b.head2300.wav"), "--audition", "--dry-run"])
    lines = capsys.readouterr().out.split("\n")[:-1]
    assert lines == [f.hex(" ") for f in host_writes("cab-upload.mmon")[:8]]


def test_cab_level_is_byte_19():
    assert up.cab_header("x")[18:] == bytes([1, 50])
    assert up.cab_header("x", 80)[18:] == bytes([1, 80])
    with pytest.raises(ValueError):
        up.cab_header("x", 101)
