"""Read the pedal's global block and report anything that would leave it silent for normal
playing. Today that is just `usb-audio`, borrowed for re-amp (see mvave.usb_audio) and normally
ON (0) the rest of the time — see the "borrowed state" invariant in skills/mvave/SKILL.md.
"""
from __future__ import annotations


def diagnose(profile, globals_bytes: bytes) -> list[str]:
    """Pure check: given a device profile and its 86-byte global block (space 2), return a list
    of human-readable problems. Empty means the pedal is set up for normal guitar-in playing."""
    problems = []
    field = profile.usb_audio_field
    value = globals_bytes[field]
    if value != 0:
        name, values = profile.global_fields[field]
        label = values[value] if value < len(values) else str(value)
        problems.append(
            f"{name} is {label} ({value}), not ON: the pedal ignores the guitar input and "
            f"processes USB playback instead. Fix: mvave global-set usb-audio 0"
        )
    return problems
