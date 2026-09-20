"""Single choke point for anything that switches the pedal's `usb-audio` global field.

With `usb-audio = RESAMPLE`, the pedal ignores the guitar input and processes USB playback
instead (that is what re-amp needs); left in that mode after the run, the rig goes silent for
normal playing until someone notices and sets it back (incident: 2026-09-19/20, `mvave reamp`
left `usb-audio = 2 (RESAMPLE)` and cost an hour of debugging — see docs/learnings.md).

`usb-audio` is **borrowed state**: any code path that changes it must go through
`borrowed_usb_audio()`, the only thing in this codebase allowed to write that field. It
snapshots the previous value, yields with the field set to the requested mode, and restores the
snapshot before the context exits — on normal return, on any exception, and on SIGINT/SIGTERM,
before the process dies. If the restore write itself fails, it does not raise (that would mask
whatever the caller was doing); it prints a loud warning to stderr with the exact command to fix
it by hand.
"""
from __future__ import annotations

import atexit
import signal
import sys
from contextlib import contextmanager

from . import protocol as p

# Signals that can end the process outside the normal try/finally control flow.
RESTORE_SIGNALS = (signal.SIGINT, signal.SIGTERM)


@contextmanager
def borrowed_usb_audio(device, mode: int | None = None):
    """Snapshot `device`'s usb-audio field, set it to `mode` (default: the profile's RESAMPLE
    value), and guarantee the snapshot is restored before this context exits.

    `device=None` is a no-op, for callers that only want to run against a pre-recorded loop
    (nothing to borrow from). `device` only needs `.profile`, `.read_global()` and `.set_u8()`
    (an `mvave.device.MVave`, or a test double).
    """
    if device is None:
        yield
        return

    prof = getattr(device, "profile", None)
    field = getattr(prof, "usb_audio_field", 0x3D)
    mode = mode if mode is not None else getattr(prof, "usb_audio_resample", 2)
    previous = device.read_global()[field]
    restored = False

    def restore() -> None:
        nonlocal restored
        if restored:
            return
        restored = True
        try:
            device.set_u8(field, previous, p.SPACE_STATUS)
        except Exception as exc:  # noqa: BLE001 - deliberately broad: this must never raise
            print(
                "mvave: FAILED to restore usb-audio after borrowing it — the pedal is likely "
                f"stuck silent to the guitar input. Fix it by hand:\n"
                f"  mvave global-set usb-audio {previous}\n"
                f"  (restore attempt failed: {exc})",
                file=sys.stderr,
            )

    previous_handlers: dict[int, object] = {}

    def on_signal(signum, frame):
        restore()
        # Put the previous handler back and hand the signal to it, so the process still reacts
        # to Ctrl-C / a kill the normal way — just after the pedal is safe again.
        signal.signal(signum, previous_handlers[signum])
        signal.raise_signal(signum)

    for sig in RESTORE_SIGNALS:
        try:
            previous_handlers[sig] = signal.signal(sig, on_signal)
        except (ValueError, OSError):
            # Not the main thread, or the platform doesn't support it: atexit below is still a
            # net for normal interpreter shutdown.
            pass

    atexit.register(restore)
    try:
        device.set_u8(field, mode, p.SPACE_STATUS)
        yield
    finally:
        restore()
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        atexit.unregister(restore)
