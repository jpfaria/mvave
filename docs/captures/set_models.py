"""Throwaway helper for the catalog sweep: set the model of several blocks over MIDI and read
back each block's 24 knob bytes (the model defaults). Usage: set_models.py b:k [b:k ...]
Appends JSON lines {block, model, params:[12 u16]} to docs/captures/model_defaults.jsonl."""
import json, sys, time, mido
from mk300 import protocol as p
name = next(n for n in mido.get_output_names() if "USB Composite" in n)
out = mido.open_output(name); inp = mido.open_input(name)
def rx(timeout=1.5):
    t = time.time() + timeout
    while time.time() < t:
        for m in inp.iter_pending():
            if m.type == "sysex": return bytes(m.bytes())
        time.sleep(0.005)
def send(fr): out.send(mido.Message("sysex", data=fr[1:-1]))
log = open("docs/captures/model_defaults.jsonl", "a")
for arg in sys.argv[1:]:
    b, k = map(int, arg.split(":"))
    for _ in inp.iter_pending(): pass
    send(p.write_u8(0x36 + b, k))
    ack = None
    while ack != p.ACK:
        ack = rx()
        assert ack is not None, "no ack"
    for _ in inp.iter_pending(): pass
    time.sleep(0.05)
    send(p.read(0x42 + 24 * b, 24))
    f = None
    while f is None or f.cls != p.CLS_READ or f.field != 0x42 + 24 * b or len(f.payload) < 24:
        r = rx(); assert r is not None, "no read reply"
        try: f = p.parse(r)
        except ValueError: f = None
    params = [int.from_bytes(f.payload[i:i+2], "little") for i in range(0, 24, 2)]
    log.write(json.dumps({"block": b, "model": k, "params": params}) + "\n")
    print(b, k, params)
