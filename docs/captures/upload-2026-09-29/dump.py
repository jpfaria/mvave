"""Dump a MIDI Monitor .mmon capture as text: one line per SysEx.

Messages that repeat 3+ times in the capture (the editor's 1 s status polling) are listed once in a
header and left out of the timeline.

Usage: python3 dump.py nam-upload.mmon > nam-upload.txt
Bytes stored by MIDI Monitor omit the leading F0 and trailing F7; this dump adds them back.
"""
import plistlib, sys

def messages(path):
    a = plistlib.loads(plistlib.load(open(path, 'rb'))['messageData'])
    o = a['$objects']
    for ref in o[1]['NS.objects']:
        m = o[ref.data]
        yield m['timeStampInNanos'], o[m['originatingEndpoint'].data], b'\xf0' + o[m['data'].data] + b'\xf7'

from collections import Counter

def main(path):
    rows = list(messages(path))
    t0 = rows[0][0]
    count = Counter((ep, data) for _, ep, data in rows)
    polling = {k for k, n in count.items() if n >= 3}
    print('# polling (left out of the timeline):')
    for (ep, data), n in count.items():
        if (ep, data) in polling:
            print(f'#   {n:4d}x {"OUT" if ep.startswith("To") else "IN "} {len(data):4d}  {data.hex(" ")}')
    print('# t(s)    dir  len  bytes')
    for t, ep, data in rows:
        if (ep, data) in polling:
            continue
        d = 'OUT' if ep.startswith('To') else 'IN '
        print(f'{(t - t0) / 1e9:9.3f} {d} {len(data):5d}  {data.hex(" ")}')

if __name__ == '__main__':
    main(sys.argv[1])
