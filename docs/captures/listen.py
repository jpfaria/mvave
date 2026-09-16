"""Log every MIDI message the MK-300 sends (full bytes) to a file. Usage: python3 listen.py OUT.log"""
import sys, time, mido
port = next(n for n in mido.get_input_names() if "USB Composite" in n)
out = open(sys.argv[1], "a", buffering=1)
with mido.open_input(port) as inp:
    out.write(f"# listening {port} {time.strftime('%H:%M:%S')}\n")
    for m in inp:
        b = bytes(m.bytes())
        out.write(f"{time.strftime('%H:%M:%S')} {time.time():.3f} <- {len(b)} {b.hex(' ')}\n")
