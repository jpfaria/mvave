"""Model catalog: every block, its models (index = value of the model byte), knob names and
the defaults the pedal loads when a model is selected. Built from mk300/catalog.json."""
from __future__ import annotations

import json
from importlib import resources

from .preset import BLOCKS, BLOCK_ID

_DATA = json.loads(resources.files(__package__).joinpath("catalog.json").read_text())
_BY_BLOCK = {b["name"]: b for b in _DATA["blocks"]}


def block_names() -> list[str]:
    return list(BLOCKS)


def models(block: str) -> list[dict]:
    return _BY_BLOCK[block.upper()]["models"]


def model(block: str, index: int) -> dict:
    ms = models(block)
    if not 0 <= index < len(ms):
        raise IndexError(f"{block} has {len(ms)} models, index {index} out of range")
    return ms[index]


def find_model(block: str, name: str) -> dict:
    """Exact (case-insensitive) name, else the number prefix of DS/AMP/CAB names ('53' -> '53J900_CH1'),
    else a unique substring match."""
    ms = models(block)
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
    raise KeyError(f"{block}: no model {name!r}" + (f" (candidates: {[m['name'] for m in hits]})" if hits else ""))


def knob_names(block: str, index: int) -> list[str]:
    return list(model(block, index)["knobs"] or [])


def knob_index(block: str, model_index: int, knob: str) -> int:
    names = [n.lower() for n in knob_names(block, model_index)]
    if knob.lower() in names:
        return names.index(knob.lower())
    hits = [i for i, n in enumerate(names) if knob.lower() in n]
    if len(hits) == 1:
        return hits[0]
    raise KeyError(f"{block} model {model_index}: no knob {knob!r} in {names}")


def block_id(block: str) -> int:
    return BLOCK_ID[block.upper()]
