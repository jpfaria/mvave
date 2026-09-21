"""Runs the bridge against real MIDI ports (mido), until Ctrl-C."""
from __future__ import annotations

import threading
import time

import mido

from ..surfaces import get as get_surface
from .daemon import Bridge
from .profile import load_profile


def find_port(hint: str, nomes: list[str]) -> str:
    achou = [n for n in nomes if hint in n]
    if not achou:
        raise SystemExit(f"nenhuma porta MIDI com {hint!r}: {nomes}")
    return achou[0]


def run(caminho_perfil: str, port: str | None = None, log=print) -> None:
    perfil = load_profile(caminho_perfil)
    surface = get_surface(perfil.surface)
    entrada = port or find_port(surface.port_hint, mido.get_input_names())
    saida = port or find_port(surface.port_hint, mido.get_output_names())

    with mido.open_output(saida) as out, mido.open_input(entrada) as inp:
        ponte = Bridge(perfil, enviar=lambda **k: out.send(mido.Message(**k)), log=log)
        threading.Thread(target=ponte.escoa, daemon=True).start()
        log(f"ponte: {surface.name} ({entrada}) -> "
            + ", ".join(b.name for b in perfil.banks))
        ponte.escolhe_banco(0)
        try:
            for msg in inp:
                ponte.on_midi(msg)
        except KeyboardInterrupt:
            log("fim")
