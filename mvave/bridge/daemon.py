"""The bridge loop: a Mackie surface in, drivers out.

Everything the surface cannot know lives here: which fader owns which target
(the profile), whether a fader may take over yet (the surface has no motor and
never reports its position), what "solo" means when the mixer has no solo bus,
and which LEDs to light back."""
from __future__ import annotations

import threading
import time

from .. import mackie
from .drivers import Unsupported, build

INTERVALO = 0.03     # s: a fader sends ~40 messages/s; write the last one
PERTO = 0.02         # takeover tolerance, in 0..1


class Bridge:
    def __init__(self, profile, enviar=None, drivers=None, log=print):
        self.profile = profile
        self.enviar = enviar or (lambda **kwargs: None)
        self.log = log
        self._drivers = drivers if drivers is not None else {}
        self.banco = 0
        self.solo_ativo = None
        self.solo_antes = {}
        self.valor_antes = {}
        self.cena_ativa = None
        self.pegou = set()
        self.ultimo = {}
        self.pendente = {}
        self.lock = threading.Lock()

    # -- drivers ---------------------------------------------------------------
    def driver(self, nome):
        if nome not in self._drivers:
            self._drivers[nome] = build(nome)
        return self._drivers[nome]

    def _ler(self, d):
        try:
            return self.driver(d.driver).read(d.target)
        except Exception:
            return None

    def _escrever(self, d, v):
        try:
            self.driver(d.driver).write(d.target, v)
            return True
        except Exception as e:
            self.log(f"  !! {d.label}: {e}")
            return False

    # -- estado ----------------------------------------------------------------
    @property
    def bank(self):
        return self.profile.bank(self.banco)

    def destino(self, fader):
        return self.bank.faders.get(fader)

    def troca_banco(self, passo):
        self.escolhe_banco((self.banco + passo) % len(self.profile.banks))

    def escolhe_banco(self, i):
        if 0 <= i < len(self.profile.banks):
            self.banco = i
            self.pegou.clear()
            self.log(f"** banco {i + 1}/{len(self.profile.banks)}: {self.bank.name}")
            self.empurra_estado()

    def empurra_estado(self):
        """Tudo o que a superficie consegue mostrar: posicao e LEDs."""
        for fader in range(1, 9):
            d = self.destino(fader)
            v = self._ler(d) if d else None
            self.enviar(**mackie.fader_position(fader - 1, v if v is not None else 0.0))
            self.enviar(**mackie.led(mackie.MUTE + fader - 1, self._mutado(fader)))
            self.enviar(**mackie.led(mackie.SOLO + fader - 1, self.solo_ativo == fader))
            self.enviar(**mackie.led(mackie.REC + fader - 1, self.cena_ativa == fader))
            self.enviar(**mackie.led(mackie.SELECT + fader - 1, self.banco == fader - 1))

    def _mutado(self, fader):
        d = self.destino(fader)
        if d is None:
            return False
        if d.mute is None:
            return d.target in self.valor_antes
        try:
            return float(self.driver(d.driver).read(d.mute)) >= 0.5
        except Exception:
            return False

    # -- faders ----------------------------------------------------------------
    def fader(self, canal, valor):
        d = self.destino(canal + 1)
        if d is None:
            return
        chave = (self.banco, canal)
        if chave not in self.pegou:
            atual = self._ler(d)
            anterior = self.ultimo.get(chave)
            cruzou = anterior is not None and (anterior - atual) * (valor - atual) < 0
            if atual is None or abs(valor - atual) <= PERTO or cruzou:
                self.pegou.add(chave)
                self.log(f"  .. fader {canal + 1} ({d.label}) assumiu")
            else:
                if anterior is None:
                    self.log(f"  .. fader {canal + 1} ({d.label}) travado: "
                             f"leve ate {atual:.2f} (esta em {valor:.2f})")
                self.ultimo[chave] = valor
                return
        self.ultimo[chave] = valor
        with self.lock:
            self.pendente[canal] = valor

    def escoa(self):
        """Aplica a ultima posicao de cada fader. Roda em thread propria."""
        while True:
            time.sleep(INTERVALO)
            self.escoa_uma_vez()

    def escoa_uma_vez(self):
        with self.lock:
            itens, self.pendente = self.pendente, {}
        for canal, v in itens.items():
            d = self.destino(canal + 1)
            if d is not None and self._escrever(d, v):
                self.enviar(**mackie.fader_position(canal, v))   # alinha o LED

    # -- botoes ----------------------------------------------------------------
    def mute(self, fader):
        d = self.destino(fader)
        if d is None:
            return
        try:
            if d.mute is not None:
                self.driver(d.driver).toggle(d.mute)
            elif d.target in self.valor_antes:          # sem mute: devolve
                self.driver(d.driver).write(d.target, self.valor_antes.pop(d.target))
            else:                                       # sem mute: zera
                self.valor_antes[d.target] = self._ler(d) or 0.0
                self.driver(d.driver).write(d.target, 0.0)
        except Exception as e:
            self.log(f"  !! mute {d.label}: {e}")
        self.empurra_estado()

    def solo(self, fader):
        """So o destino deste fader toca -- dentro do grupo dele."""
        alvo = self.destino(fader)
        if alvo is None:
            return
        pares = [(n, d) for n, d in self.bank.faders.items() if d.group == alvo.group]
        if self.solo_ativo == fader:
            for n, d in pares:
                if d.mute is not None:
                    self._restaura_mute(d, self.solo_antes.get(n, False))
                elif d.target in self.valor_antes:
                    self._escrever(d, self.valor_antes.pop(d.target))
            self.solo_ativo, self.solo_antes = None, {}
            self.log("  -> solo off")
        else:
            if self.solo_ativo is None:
                self.solo_antes = {n: self._mutado(n) for n, _ in pares}
            for n, d in pares:
                calar = n != fader
                if d.mute is not None:
                    self._restaura_mute(d, calar)
                elif calar:
                    self.valor_antes.setdefault(d.target, self._ler(d) or 0.0)
                    self._escrever(d, 0.0)
                elif d.target in self.valor_antes:
                    self._escrever(d, self.valor_antes.pop(d.target))
            self.solo_ativo = fader
            self.log(f"  -> solo em {alvo.label}")
        self.empurra_estado()

    def _restaura_mute(self, d, mudo):
        try:
            drv = self.driver(d.driver)
            if (float(drv.read(d.mute)) >= 0.5) != mudo:
                drv.toggle(d.mute)
        except Exception as e:
            self.log(f"  !! mute {d.label}: {e}")

    def cena(self, fader):
        d = self.destino(fader)
        if d is None:
            return
        try:
            nome = self.driver(d.driver).load_scene(fader - 1)
            self.cena_ativa = fader
            self.solo_ativo, self.solo_antes = None, {}
            self.pegou.clear()
            self.log(f"  -> cena {nome}")
        except Unsupported as e:
            self.log(f"  !! cena: {e}")
        self.empurra_estado()

    # -- entrada ---------------------------------------------------------------
    def on_midi(self, msg):
        evento = mackie.decode(msg)
        if isinstance(evento, mackie.Fader):
            self.fader(evento.channel, evento.value)
        elif isinstance(evento, mackie.Button) and evento.pressed:
            self.botao(evento)

    def botao(self, b):
        acoes = self.bank.buttons
        if b.kind in ("bank_right", "arrow_right"):
            self.troca_banco(+1)
        elif b.kind in ("bank_left", "arrow_left"):
            self.troca_banco(-1)
        elif b.kind == "mute":
            self.mute(b.channel + 1)
        elif b.kind == "solo":
            self.solo(b.channel + 1)
        elif b.kind == "rec" and acoes.get("rec", "scene") == "scene":
            self.cena(b.channel + 1)
        elif b.kind == "select" and acoes.get("select", "bank") == "bank":
            self.escolhe_banco(b.channel)
