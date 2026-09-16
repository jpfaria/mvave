"""One profile per M-VAVE pedal the M-EFCS editor supports. Only the MK-300 is mapped so far;
a new pedal = a new module here (preset struct, global fields, catalog) — the protocol is shared."""
from __future__ import annotations

from . import mk300

PROFILES = {"mk300": mk300.PROFILE}
DEFAULT = "mk300"


def get(name: str | None = None):
    name = (name or DEFAULT).lower().replace("-", "")
    try:
        return PROFILES[name]
    except KeyError:
        raise SystemExit(f"unknown device {name!r}; known: {', '.join(PROFILES)}")
