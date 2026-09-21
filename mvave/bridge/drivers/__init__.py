"""One driver per thing a fader can control. Each speaks its own dialect; the
bridge only ever calls this interface:

    read(target)   -> 0..1 (or None when the driver cannot read it back)
    write(target, value)
    toggle(target) -> the new state
    scenes()       -> list of names
    load_scene(i)

A driver that cannot do something raises Unsupported -- the bridge turns that
into a warning, never a crash."""
from __future__ import annotations


class Unsupported(Exception):
    pass


class Driver:
    name = "driver"

    def read(self, target):
        raise Unsupported(f"{self.name}: read {target}")

    def write(self, target, value):
        raise Unsupported(f"{self.name}: write {target}")

    def toggle(self, target):
        raise Unsupported(f"{self.name}: toggle {target}")

    def scenes(self):
        return []

    def load_scene(self, index):
        raise Unsupported(f"{self.name}: scenes")


def build(name: str, **opts) -> Driver:
    from . import hd8, mac
    tabela = {"hd8": hd8.HD8, "mac": mac.MacVolume, "app": mac.AppVolume}
    try:
        return tabela[name](**opts)
    except KeyError:
        raise SystemExit(f"unknown driver {name!r}; known: {', '.join(tabela)}")
