"""macOS volume: the system output, and one application's own volume."""
from __future__ import annotations

import subprocess

from . import Driver, Unsupported


def _osascript(script: str) -> str:
    out = subprocess.run(["osascript", "-e", script],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


class MacVolume(Driver):
    """System output volume.

    Only works when the default output is a device macOS controls. With an
    interface like the Quantum HD 8 selected, AppleScript answers
    "missing value" for output volume -- the volume lives in the interface,
    not in the OS -- and this driver says so instead of guessing."""
    name = "mac"

    _SEM_CONTROLE = ("a saida padrao do Mac nao tem volume controlavel pelo "
                     "sistema (interface de audio selecionada)")

    def read(self, target=None):
        bruto = _osascript("output volume of (get volume settings)")
        if bruto == "missing value":
            raise Unsupported(self._SEM_CONTROLE)
        return int(bruto) / 100

    def write(self, target, value):
        self.read()                      # falha cedo, com a razao certa
        _osascript(f"set volume output volume {round(value * 100)}")

    def toggle(self, target=None):
        bruto = _osascript("output muted of (get volume settings)")
        if bruto == "missing value":
            raise Unsupported(self._SEM_CONTROLE)
        mudo = bruto == "true"
        _osascript(f"set volume {'without' if mudo else 'with'} output muted")
        return not mudo


class AppVolume(Driver):
    """target = the application name, e.g. "Spotify"."""
    name = "app"

    def read(self, target):
        try:
            return int(_osascript(f'tell application "{target}" to sound volume')) / 100
        except subprocess.CalledProcessError as e:
            raise Unsupported(f"{target} nao respondeu: {e}") from e

    def write(self, target, value):
        _osascript(f'tell application "{target}" to set sound volume to {round(value * 100)}')

    def toggle(self, target):
        _osascript(f'tell application "{target}" to playpause')
        return True
