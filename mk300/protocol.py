"""MK-300 SysEx protocol: frame layout, 7-bit packing, checksum.

Reverse-engineered from the M-EFCS editor (3.7.1413) talking to firmware V73 on
2026-09-16; see docs/protocol.md.  Every frame is

    F0 00 32 | CLS | CMD(4) | 02 | FIELD(4) | SUB(4) | packed(payload + ck8) | F7

where the 14 header bytes are plain 7-bit values, FIELD is a byte offset inside the
addressed memory space, SUB = (len << 4 | space) written as little-endian 7-bit
digits, and the payload plus one checksum byte are packed LSB-first, 7 bits per
SysEx byte.  ck8 = 0xFB - (sum(payload) + sum(bytes of u32 FIELD) + sum(bytes of
u32 (len << 8 | space << 4))) mod 256 -- the 8-bit bytes, not the 7-bit digits; CLS and CMD are not covered.
"""
from __future__ import annotations

from dataclasses import dataclass

MANUFACTURER = b"\x00\x32"

CLS_WRITE = 0x09     # host -> pedal, carries data
CLS_READ = 0x0D      # host -> pedal query, and pedal -> host data
CLS_ACK = 0x01

CMD_READ = 0x41
CMD_WRITE_U8 = 0x49  # 1-byte fields: models, on/off, load preset
CMD_WRITE_U16 = 0x51 # 2-byte fields: knobs, preset vol / pan / bpm

SPACE_PRESET = 0x1   # the edit buffer (448-byte preset struct)
SPACE_STATUS = 0x2   # 86-byte status block the editor polls every second
SPACE_COMMAND = 0xE  # "load preset N" = write 01 at offset N

HEADER_LEN = 14
ACK = bytes.fromhex("f0 00 32 01 08 00 00 00 00 7f 01 f7")


def pack7(data: bytes) -> bytes:
    """8-bit bytes -> 7-bit SysEx bytes, LSB first (bit i of the stream = bit i)."""
    bits = 0
    n = 0
    out = bytearray()
    for b in data:
        bits |= b << n
        n += 8
        while n >= 7:
            out.append(bits & 0x7F)
            bits >>= 7
            n -= 7
    if n:
        out.append(bits & 0x7F)
    return bytes(out)


def unpack7(data: bytes) -> bytes:
    """Inverse of pack7; leftover bits (fewer than 8) are dropped."""
    bits = 0
    n = 0
    out = bytearray()
    for b in data:
        bits |= (b & 0x7F) << n
        n += 7
        while n >= 8:
            out.append(bits & 0xFF)
            bits >>= 8
            n -= 8
    return bytes(out)


def _u32_7(v: int) -> bytes:
    return bytes([v & 0x7F, (v >> 7) & 0x7F, (v >> 14) & 0x7F, (v >> 21) & 0x7F])


def _from_u32_7(b: bytes) -> int:
    return b[0] | b[1] << 7 | b[2] << 14 | b[3] << 21


def checksum(field: int, length: int, space: int, payload: bytes) -> int:
    sub8 = (length << 8) | (space << 4)
    total = sum(payload) + sum(field.to_bytes(4, "little")) + sum(sub8.to_bytes(4, "little"))
    return (0xFB - total) & 0xFF


@dataclass(frozen=True)
class Frame:
    cls: int
    cmd: int          # CMD(4) as an integer (7-bit digits, little-endian)
    field: int        # byte offset
    length: int       # bytes addressed
    space: int        # memory space
    payload: bytes    # decoded 8-bit payload (without the checksum)

    @property
    def cmd_bytes(self) -> bytes:
        return _u32_7(self.cmd)


def build(cls: int, cmd: int, field: int, length: int, space: int, payload: bytes = b"") -> bytes:
    """Encode a frame.  `length` is the size of the addressed object (for a read it is
    how many bytes to read; for a write it equals len(payload))."""
    ck = checksum(field, length, space, payload)
    hdr = bytes([cls]) + _u32_7(cmd) + b"\x02" + _u32_7(field) + _u32_7((length << 4) | space)
    return b"\xf0" + MANUFACTURER + hdr + pack7(payload + bytes([ck])) + b"\xf7"


def parse(frame: bytes, verify: bool = True) -> Frame:
    if frame[:3] != b"\xf0" + MANUFACTURER or frame[-1] != 0xF7:
        raise ValueError("not an MK-300 frame")
    body = frame[3:-1]
    if len(body) < HEADER_LEN:
        raise ValueError("short frame")
    hdr, tail = body[:HEADER_LEN], body[HEADER_LEN:]
    sub = _from_u32_7(hdr[10:14])
    length, space = sub >> 4, sub & 0xF
    dec = unpack7(tail)
    if not dec:
        raise ValueError("no checksum")
    payload, ck = dec[:-1], dec[-1]
    field = _from_u32_7(hdr[6:10])
    if verify and ck != checksum(field, length, space, payload):
        raise ValueError(f"bad checksum {ck:02x} != {checksum(field, length, space, payload):02x}")
    return Frame(hdr[0], _from_u32_7(hdr[1:5]), field, length, space, payload)


def is_ack(frame: bytes) -> bool:
    return frame == ACK


# Convenience builders -----------------------------------------------------------

def read(field: int, length: int, space: int = SPACE_PRESET) -> bytes:
    return build(CLS_READ, CMD_READ, field, length, space)


def write_u8(field: int, value: int, space: int = SPACE_PRESET) -> bytes:
    return build(CLS_WRITE, CMD_WRITE_U8, field, 1, space, bytes([value & 0xFF]))


def write_u16(field: int, value: int, space: int = SPACE_PRESET) -> bytes:
    return build(CLS_WRITE, CMD_WRITE_U16, field, 2, space, (value & 0xFFFF).to_bytes(2, "little"))


def load_preset(index: int) -> bytes:
    """0-based preset index (editor label [001] = 0)."""
    return build(CLS_WRITE, CMD_WRITE_U8, index, 1, SPACE_COMMAND, b"\x01")


POLL = read(0, 86, SPACE_STATUS)          # what the editor sends every second
READ_PRESET = read(0, 448, SPACE_PRESET)  # the whole edit buffer
