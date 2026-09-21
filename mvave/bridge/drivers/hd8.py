"""PreSonus Quantum HD 8, through the `quantum-hd8` library (UCNet).

The HD 8 does not receive MIDI: a full sweep of CC, pitch bend and notes on
both of its CoreMIDI ports changed none of its 1419 parameters (2026-09-20).
Every write here goes to `ucdaemon` over TCP instead."""
from __future__ import annotations

from . import Driver, Unsupported


class HD8(Driver):
    name = "hd8"

    def __init__(self, client=None):
        if client is None:
            try:
                from quantum_hd8.client import Client
            except ImportError as e:      # pragma: no cover - depends on the host
                raise Unsupported("quantum-hd8 nao instalado: "
                                  "pipx install git+https://github.com/jpfaria/quantum-hd8") from e
            client = Client()
            client.connect()
        self.cli = client

    def read(self, target):
        return float(self.cli.get(target))

    def write(self, target, value):
        self.cli.set_raw(target, max(0.0, min(1.0, value)))

    def toggle(self, target):
        ligado = float(self.cli.get(target)) >= 0.5
        self.cli.set(target, 0 if ligado else 1)
        return not ligado

    def scenes(self):
        return [n.removesuffix(".scene") for n in self.cli.scenes]

    def load_scene(self, index):
        nomes = self.scenes()
        if not 0 <= index < len(nomes):
            raise Unsupported(f"cena {index + 1} nao existe (tem {len(nomes)})")
        self.cli.load_scene(nomes[index], keep_gains=True)
        return nomes[index]
