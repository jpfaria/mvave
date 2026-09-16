"""Golden vectors captured from the M-EFCS editor on 2026-09-16 (docs/captures)."""
import pytest

from mk300 import protocol as p

EDITOR = {
    "preset vol 60": "F0 00 32 09 51 00 00 00 02 18 00 00 00 21 00 00 00 3C 00 54 04 F7",
    "preset vol 72": "F0 00 32 09 51 00 00 00 02 18 00 00 00 21 00 00 00 48 00 24 04 F7",
    "bpm 111": "F0 00 32 09 51 00 00 00 02 1A 00 00 00 21 00 00 00 6F 00 00 03 F7",
    "bpm 133": "F0 00 32 09 51 00 00 00 02 1A 00 00 00 21 00 00 00 05 01 28 02 F7",
    "wah knob 0 = 70": "F0 00 32 09 51 00 00 00 02 42 00 00 00 21 00 00 00 46 00 04 03 F7",
    "pan R17": "F0 00 32 09 51 00 00 00 02 1C 00 00 00 21 00 00 00 11 00 70 05 F7",
    "wah model 1": "F0 00 32 09 49 00 00 00 02 36 00 00 00 11 00 00 00 01 66 02 F7",
    "fx off": "F0 00 32 09 49 00 00 00 02 2C 00 00 00 11 00 00 00 00 7C 02 F7",
    "poll": "F0 00 32 0D 41 00 00 00 02 00 00 00 00 62 0A 00 00 05 01 F7",
    "read wah params": "F0 00 32 0D 41 00 00 00 02 42 00 00 00 01 03 00 00 11 01 F7",
    "read preset": "F0 00 32 0D 41 00 00 00 02 00 00 00 00 01 38 00 00 2A 00 F7",
    "load preset 2": "F0 00 32 09 49 00 00 00 02 02 00 00 00 1E 00 00 00 01 2E 00 F7",
    "load preset 0": "F0 00 32 09 49 00 00 00 02 00 00 00 00 1E 00 00 00 01 32 00 F7",
}
BUILT = {
    "preset vol 60": p.write_u16(0x18, 60),
    "preset vol 72": p.write_u16(0x18, 72),
    "bpm 111": p.write_u16(0x1A, 111),
    "bpm 133": p.write_u16(0x1A, 133),
    "wah knob 0 = 70": p.write_u16(0x42, 70),
    "pan R17": p.write_u16(0x1C, 17),
    "wah model 1": p.write_u8(0x36, 1),
    "fx off": p.write_u8(0x2C, 0),
    "poll": p.POLL,
    "read wah params": p.read(0x42, 24),
    "read preset": p.READ_PRESET,
    "load preset 2": p.load_preset(2),
    "load preset 0": p.load_preset(0),
}


@pytest.mark.parametrize("name", sorted(EDITOR))
def test_build_matches_editor(name):
    assert BUILT[name].hex(" ") == bytes.fromhex(EDITOR[name]).hex(" ")


@pytest.mark.parametrize("name", sorted(EDITOR))
def test_parse_roundtrip(name):
    f = p.parse(bytes.fromhex(EDITOR[name]))
    assert p.build(f.cls, f.cmd, f.field, f.length, f.space, f.payload) == bytes.fromhex(EDITOR[name])


def test_pack_unpack():
    for data in (b"", b"\x00", b"\xff", b"JM-OD\x00", bytes(range(256))):
        assert p.unpack7(p.pack7(data)) == data


def test_bad_checksum_rejected():
    bad = bytearray(bytes.fromhex(EDITOR["poll"]))
    bad[-3] ^= 1
    with pytest.raises(ValueError):
        p.parse(bytes(bad))
