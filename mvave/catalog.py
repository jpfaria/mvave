"""Model catalog of a device profile: every block, its models (index = value of the model byte),
knob names and the defaults the pedal loads when a model is selected."""
from __future__ import annotations

import json
from importlib import resources


class Catalog:
    def __init__(self, profile):
        self.profile = profile
        data = json.loads(resources.files("mvave.devices").joinpath(profile.catalog_file).read_text())
        self._by_block = {b["name"]: b for b in data["blocks"]}
        self.blocks = list(profile.blocks)
        self.block_id = {name: i for i, name in enumerate(self.blocks)}

    def block_names(self) -> list[str]:
        return list(self.blocks)

    def block(self, name: str) -> int:
        return self.block_id[name.upper()]

    def models(self, block: str) -> list[dict]:
        return self._by_block[block.upper()]["models"]

    def model(self, block: str, index: int) -> dict:
        ms = self.models(block)
        if not 0 <= index < len(ms):
            raise IndexError(f"{block} has {len(ms)} models, index {index} out of range")
        return ms[index]

    def find_model(self, block: str, name: str) -> dict:
        """Exact (case-insensitive) name, else the number prefix of numbered names ('53' -> '53J900_CH1'),
        else a unique substring match, else a bare 0-based index."""
        ms = self.models(block)
        low = name.lower()
        for m in ms:
            if m["name"].lower() == low:
                return m
        if name.isdigit():
            for m in ms:
                if m["name"].startswith(name) and not m["name"][len(name):len(name) + 1].isdigit():
                    return m
        hits = [m for m in ms if low in m["name"].lower()]
        if len(hits) == 1:
            return hits[0]
        if name.isdigit() and int(name) < len(ms):
            return ms[int(name)]
        raise KeyError(f"{block}: no model {name!r}" + (f" (candidates: {[m['name'] for m in hits]})" if hits else ""))

    def knob_names(self, block: str, index: int) -> list[str]:
        return list(self.model(block, index)["knobs"] or [])

    def knob_index(self, block: str, model_index: int, knob: str) -> int:
        names = [n.lower() for n in self.knob_names(block, model_index)]
        if knob.lower() in names:
            return names.index(knob.lower())
        hits = [i for i, n in enumerate(names) if knob.lower() in n]
        if len(hits) == 1:
            return hits[0]
        raise KeyError(f"{block} model {model_index}: no knob {knob!r} in {names}")


def load(profile=None) -> Catalog:
    from . import devices
    return Catalog(profile or devices.get())
