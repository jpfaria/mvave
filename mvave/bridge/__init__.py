"""Bridge: a control surface drives other gear through drivers.

The surface knows nothing about the rig and the rig knows nothing about MIDI --
a profile (YAML) says what each fader and button touches. See docs/bridge.md."""
from __future__ import annotations

from .profile import Profile, load_profile      # noqa: F401
from .daemon import Bridge                      # noqa: F401
