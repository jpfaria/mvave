"""The rig profile: what each fader and button of a bank is wired to.

    banks:
      - name: HD 8
        faders:
          1: {driver: hd8, target: global/mainOutVolume, label: MAIN, group: out}
          5: {driver: hd8, target: line/ch1/volume, label: GUITA 1, group: in,
              mute: line/ch1/mute}
        buttons:
          rec: scene        # R n loads scene n of that fader's driver
          select: bank      # [] n selects bank n

A fader with `mute:` is muted with that parameter; one without is muted by
zeroing its own value and remembering it. `group` keeps solo honest: soloing an
input must not mute the outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Destino:
    driver: str
    target: str | None = None
    label: str = ""
    group: str = "out"
    mute: str | None = None


@dataclass(frozen=True)
class Bank:
    name: str
    faders: dict[int, Destino] = field(default_factory=dict)
    buttons: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Profile:
    surface: str
    banks: list[Bank]

    def bank(self, i: int) -> Bank:
        return self.banks[i % len(self.banks)]


def _destino(bruto: dict) -> Destino:
    faltando = {"driver"} - set(bruto)
    if faltando:
        raise SystemExit(f"destino sem {', '.join(faltando)}: {bruto}")
    return Destino(driver=bruto["driver"], target=bruto.get("target"),
                   label=bruto.get("label", bruto.get("target", "")),
                   group=bruto.get("group", "out"), mute=bruto.get("mute"))


def parse_profile(dados: dict) -> Profile:
    bancos = dados.get("banks") or []
    if not bancos:
        raise SystemExit("perfil sem banks")
    return Profile(
        surface=dados.get("surface", "smc-mixer"),
        banks=[Bank(name=b.get("name", f"banco {i + 1}"),
                    faders={int(k): _destino(v) for k, v in (b.get("faders") or {}).items()},
                    buttons=dict(b.get("buttons") or {}))
               for i, b in enumerate(bancos)],
    )


def load_profile(caminho: str | Path) -> Profile:
    caminho = Path(caminho).expanduser()
    if not caminho.exists():
        raise SystemExit(f"perfil nao encontrado: {caminho}")
    return parse_profile(yaml.safe_load(caminho.read_text()) or {})
