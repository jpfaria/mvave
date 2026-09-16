"""mk300 command line. Every command talks to the pedal over USB except `models`, `params`,
`bank` and `resolve`, which only read the catalog / files."""
from __future__ import annotations

import argparse
import sys

from . import catalog as cat
from . import preset as pr
from . import protocol as p

GLOBAL_FIELDS = {  # offset in space 2 -> (name, values)   (see docs/protocol.md)
    0x38: ("ab-convert", ["OFF", "ON"]),
    0x3C: ("rch", ["Nor", "Dry", "NoCAB"]),
    0x3D: ("usb-audio", ["ON", "OFF", "RESAMPLE", "DRY"]),
}


def _dev(args):
    from .device import MK300
    return MK300(args.port)


def _block(name: str) -> int:
    try:
        return cat.block_id(name)
    except KeyError:
        sys.exit(f"unknown block {name!r}; blocks: {', '.join(pr.BLOCKS)}")


def _slot(s: str) -> int:
    """'[003]', '003', '3' -> 2 (0-based)."""
    n = int(s.strip("[]"))
    if not 1 <= n <= 160:
        sys.exit("presets are 1..160")
    return n - 1


def show_preset(ps: pr.Preset, index: int | None = None) -> str:
    head = f"[{index + 1:03d}] " if index is not None else ""
    lines = [f"{head}{ps.name}   vol {ps.volume}  bpm {ps.bpm}  pan {ps.pan:+d}",
             "chain: " + " > ".join(pr.BLOCKS[b] for b in ps.chain)]
    for b, bname in enumerate(pr.BLOCKS):
        m = ps.model(b)
        try:
            md = cat.model(bname, m)
            knobs = md["knobs"] or []
            mname = md["name"]
        except IndexError:
            knobs, mname = [], f"model {m}?"
        vals = ps.knobs(b)
        kv = "  ".join(f"{k}={vals[i]}" for i, k in enumerate(knobs))
        lines.append(f"  {'on ' if ps.enabled(b) else 'off'} {bname:<4} {b:2d}:{m:<3d} {mname:<16} {kv}")
    return "\n".join(lines)


def cmd_show(a):
    with _dev(a) as d:
        idx = d.current_preset_index()
        print(show_preset(d.read_preset(), idx))


def cmd_load(a):
    with _dev(a) as d:
        d.load_preset(_slot(a.preset))
        print(show_preset(d.read_preset(), _slot(a.preset)))


def cmd_param(a):
    b = _block(a.block)
    with _dev(a) as d:
        ps = d.read_preset()
        k = int(a.knob) if a.knob.isdigit() else cat.knob_index(a.block, ps.model(b), a.knob)
        d.set_u16(pr.knob_offset(b, k), int(a.value))
        print(f"{a.block} knob {k} = {a.value}")


def cmd_model(a):
    b = _block(a.block)
    m = cat.find_model(a.block, a.model)
    with _dev(a) as d:
        d.set_u8(pr.model_offset(b), m["index"])
        vals = d.read(pr.knob_offset(b, 0), pr.KNOB_BYTES)
        knobs = m["knobs"] or []
        got = [int.from_bytes(vals[i:i + 2], "little", signed=True) for i in range(0, len(vals), 2)]
        print(f"{a.block} = {m['index']} {m['name']}: " + "  ".join(f"{k}={got[i]}" for i, k in enumerate(knobs)))


def cmd_enable(a):
    b = _block(a.block)
    on = a.state.lower() in ("on", "1", "true")
    with _dev(a) as d:
        d.set_u8(pr.enabled_offset(b), 1 if on else 0)
        print(f"{a.block} {'on' if on else 'off'}")


def _simple_u16(offset):
    def run(a):
        with _dev(a) as d:
            d.set_u16(offset, int(a.value))
            print(a.value)
    return run


def cmd_presets(a):
    with _dev(a) as d:
        cur = d.current_preset_index()
        for i in range(160):
            print(f"{'*' if i == cur else ' '} [{i + 1:03d}] {d.read_slot(i).name}")


def cmd_read(a):
    with _dev(a) as d:
        ps = d.read_slot(_slot(a.preset))
    if a.hex:
        print(ps.raw.hex())
    else:
        print(show_preset(ps, _slot(a.preset)))


def cmd_save(a):
    """Store the edit buffer into slot N under NAME (the editor's "Save to")."""
    slot = _slot(a.preset)
    with _dev(a) as d:
        target = d.read_slot(slot).name
        if target and not target.startswith("USER PRESET") and not a.overwrite:
            sys.exit(f"[{slot + 1:03d}] is named {target!r}: pass --overwrite to replace it")
        img = bytearray(d.read_preset().raw)
        img[0:20] = a.name.encode("latin-1")[:20].ljust(20, b"\0")
        d.save_preset(slot, bytes(img))
        print(show_preset(d.read_preset(), slot))


def cmd_copy(a):
    src, dst = _slot(a.src), _slot(a.dst)
    with _dev(a) as d:
        target = d.read_slot(dst).name
        if target and not target.startswith("USER PRESET") and not a.overwrite:
            sys.exit(f"[{dst + 1:03d}] is named {target!r}: pass --overwrite to replace it")
        img = bytearray(d.read_slot(src).raw)
        if a.name:
            img[0:20] = a.name.encode("latin-1")[:20].ljust(20, b"\0")
        d.save_preset(dst, bytes(img))
        print(f"[{src + 1:03d}] -> [{dst + 1:03d}] {pr.Preset(bytes(img)).name}")


def cmd_rename(a):
    with _dev(a) as d:
        d.write_bytes(pr.OFF_NAME, a.name.encode("latin-1")[:20].ljust(20, b"\0"))
        print(d.read_preset().name)


def cmd_chain(a):
    ids = [_block(b) for b in a.blocks]
    if sorted(ids) != list(range(11)):
        sys.exit("give all 11 blocks once: " + " ".join(pr.BLOCKS))
    with _dev(a) as d:
        d.write_bytes(pr.OFF_CHAIN, bytes(ids))
        print(" > ".join(pr.BLOCKS[b] for b in d.read_preset().chain))


def cmd_reamp(a):
    from .reamp import reamp, NoSignal
    with _dev(a) as d:
        try:
            r = reamp(a.di, a.out, tail_s=a.tail, mono=a.mono, device=d)
        except NoSignal as e:
            sys.exit(f"no signal: {e}")
    print(f"{a.out}: {r.frames} frames, {r.rms_db} dBFS")


def cmd_global(a):
    with _dev(a) as d:
        g = d.read_global()
    print(g.hex(" "))
    print(f"current preset: [{g[0] + 1:03d}]")
    for off, (name, values) in GLOBAL_FIELDS.items():
        v = g[off]
        print(f"  {name:<12} {off:#04x} = {v} ({values[v] if v < len(values) else '?'})")


def cmd_global_set(a):
    offs = {n: o for o, (n, _) in GLOBAL_FIELDS.items()}
    if a.name not in offs:
        sys.exit(f"known global fields: {', '.join(offs)}")
    off = offs[a.name]
    values = GLOBAL_FIELDS[off][1]
    v = int(a.value) if a.value.isdigit() else [x.lower() for x in values].index(a.value.lower())
    with _dev(a) as d:
        d.set_u8(off, v, p.SPACE_STATUS)
        print(f"{a.name} = {v} ({values[v]})")


def cmd_models(a):
    for m in cat.models(a.block):
        knobs = ", ".join(m["knobs"] or [])
        print(f"{m['index']:3d}  {m['name']:<20} {knobs}")


def cmd_params(a):
    m = cat.find_model(a.block, a.model)
    for i, k in enumerate(m["knobs"] or []):
        dflt = m.get("defaults", [])
        print(f"{i:2d}  {k:<12} default {dflt[i] if i < len(dflt) else '?'}")


def cmd_bank(a):
    data = open(a.file, "rb").read()
    for i, ps in enumerate(pr.parse_bank(data)):
        if a.verbose:
            print(show_preset(ps, i)); print()
        else:
            print(f"[{i + 1:03d}] {ps.name}")


def cmd_resolve(a):
    from .resolve import resolve
    for m, score in resolve(a.block, a.query)[:a.n]:
        print(f"{score:4.2f}  {m['index']:3d}  {m['name']}")


def cmd_listen(a):
    with _dev(a) as d:
        last = None
        import time
        end = time.time() + a.seconds
        while time.time() < end:
            r = d.receive(1.0)
            if r is None:
                continue
            try:
                f = p.parse(r)
            except ValueError:
                continue
            if f.space == p.SPACE_STATUS and f.payload and f.payload[0] != last:
                last = f.payload[0]
                print(f"preset [{last + 1:03d}]")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mk300", description="M-VAVE MK-300 over USB without the editor")
    ap.add_argument("--port", help="MIDI port name (default: the one containing 'USB Composite Device')")
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("show", help="the edit buffer: name, chain, models, knobs"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("load", help="load preset N (1..160) and show it"); s.add_argument("preset"); s.set_defaults(fn=cmd_load)
    s = sub.add_parser("param", help="set a knob of a block: param AMP Gain 60 (knob by name or 0-based index)")
    s.add_argument("block"); s.add_argument("knob"); s.add_argument("value"); s.set_defaults(fn=cmd_param)
    s = sub.add_parser("model", help="put a model in a block: model AMP 53 | model DLY 'Analog' (knobs reset to defaults)")
    s.add_argument("block"); s.add_argument("model"); s.set_defaults(fn=cmd_model)
    s = sub.add_parser("enable", help="block on/off: enable DLY on"); s.add_argument("block"); s.add_argument("state"); s.set_defaults(fn=cmd_enable)
    s = sub.add_parser("volume", help="preset volume 0-100"); s.add_argument("value"); s.set_defaults(fn=_simple_u16(pr.OFF_VOL))
    s = sub.add_parser("bpm", help="preset tempo"); s.add_argument("value"); s.set_defaults(fn=_simple_u16(pr.OFF_BPM))
    s = sub.add_parser("pan", help="preset pan: 0 = C, +17 = R17, negative = L"); s.add_argument("value"); s.set_defaults(fn=_simple_u16(pr.OFF_PAN))
    s = sub.add_parser("presets", help="the 160 stored presets (* = current)"); s.set_defaults(fn=cmd_presets)
    s = sub.add_parser("read", help="a stored preset straight from flash, without loading it"); s.add_argument("preset"); s.add_argument("--hex", action="store_true"); s.set_defaults(fn=cmd_read)
    s = sub.add_parser("save", help="store the edit buffer into slot N as NAME (refuses a named slot without --overwrite)")
    s.add_argument("preset"); s.add_argument("name"); s.add_argument("--overwrite", action="store_true"); s.set_defaults(fn=cmd_save)
    s = sub.add_parser("copy", help="copy a stored preset to another slot: copy 3 150 [NAME]")
    s.add_argument("src"); s.add_argument("dst"); s.add_argument("name", nargs="?"); s.add_argument("--overwrite", action="store_true"); s.set_defaults(fn=cmd_copy)
    s = sub.add_parser("rename", help="rename the edit buffer (save afterwards)"); s.add_argument("name"); s.set_defaults(fn=cmd_rename)
    s = sub.add_parser("chain", help="signal order of the 11 blocks: chain WAH FX GATE DS AMP CAB EQ MOD REV DLY VOL (unverified in the editor: byte-wise writes)")
    s.add_argument("blocks", nargs=11); s.set_defaults(fn=cmd_chain)
    s = sub.add_parser("reamp", help="play DI.wav through the pedal over USB audio (USB Audio = RESAMPLE) and record OUT.wav")
    s.add_argument("di"); s.add_argument("out"); s.add_argument("--tail", type=float, default=2.0); s.add_argument("--mono", action="store_true"); s.set_defaults(fn=cmd_reamp)
    s = sub.add_parser("global", help="read the global block (space 2)"); s.set_defaults(fn=cmd_global)
    s = sub.add_parser("global-set", help="write ONE known global field: global-set rch Dry"); s.add_argument("name"); s.add_argument("value"); s.set_defaults(fn=cmd_global_set)
    s = sub.add_parser("models", help="catalog: models of a block"); s.add_argument("block"); s.set_defaults(fn=cmd_models)
    s = sub.add_parser("params", help="catalog: knobs and defaults of a model"); s.add_argument("block"); s.add_argument("model"); s.set_defaults(fn=cmd_params)
    s = sub.add_parser("bank", help="list a bank file (the editor's mk300_am4_preset.bin)"); s.add_argument("file"); s.add_argument("-v", "--verbose", action="store_true"); s.set_defaults(fn=cmd_bank)
    s = sub.add_parser("resolve", help="which model is based on a real-world unit: resolve AMP 'Marshall JCM800'")
    s.add_argument("block"); s.add_argument("query"); s.add_argument("-n", type=int, default=5); s.set_defaults(fn=cmd_resolve)
    s = sub.add_parser("listen", help="print the preset index whenever it changes (footswitches)"); s.add_argument("seconds", type=int, nargs="?", default=60); s.set_defaults(fn=cmd_listen)

    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help(); return 0
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
