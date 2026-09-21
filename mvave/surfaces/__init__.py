"""Control surfaces: M-VAVE gear that *sends* control instead of processing audio.

They do not speak M-EFCS (that is `mvave.protocol`, for the pedals in
`mvave.devices`) -- a surface speaks Mackie Control, in `mvave.mackie`."""
from __future__ import annotations

from . import smc_mixer

SURFACES = {"smcmixer": smc_mixer.SURFACE}
DEFAULT = "smc-mixer"


def get(name: str | None = None):
    key = (name or DEFAULT).lower().replace("-", "").replace("_", "")
    try:
        return SURFACES[key]
    except KeyError:
        raise SystemExit(f"unknown surface {name!r}; known: {', '.join(SURFACES)}")
