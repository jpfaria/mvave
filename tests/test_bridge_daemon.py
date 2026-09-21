import mido
import pytest

from mvave import mackie
from mvave.bridge import daemon, profile
from mvave.bridge.drivers import Driver, Unsupported


class FakeDriver(Driver):
    name = "fake"

    def __init__(self):
        self.valores = {"main": 0.5, "g1": 0.2, "g2": 0.8,
                        "main/mute": 0.0, "g1/mute": 0.0, "g2/mute": 0.0}
        self.carregou = None

    def read(self, target):
        return self.valores[target]

    def write(self, target, value):
        self.valores[target] = value

    def toggle(self, target):
        novo = 0.0 if self.valores[target] >= 0.5 else 1.0
        self.valores[target] = novo
        return novo >= 0.5

    def scenes(self):
        return ["UMA", "OUTRA"]

    def load_scene(self, index):
        if index >= 2:
            raise Unsupported("nao existe")
        self.carregou = self.scenes()[index]
        return self.carregou


PERFIL = {"banks": [
    {"name": "rig", "faders": {
        1: {"driver": "fake", "target": "main", "label": "MAIN", "group": "out",
            "mute": "main/mute"},
        2: {"driver": "fake", "target": "fone", "label": "FONE", "group": "out"},
        5: {"driver": "fake", "target": "g1", "label": "G1", "group": "in",
            "mute": "g1/mute"},
        6: {"driver": "fake", "target": "g2", "label": "G2", "group": "in",
            "mute": "g2/mute"}}},
    {"name": "mac", "faders": {1: {"driver": "fake", "target": "main"}}},
]}


@pytest.fixture
def ponte():
    d = FakeDriver()
    d.valores["fone"] = 0.4
    b = daemon.Bridge(profile.parse_profile(PERFIL), enviar=lambda **k: None,
                      drivers={"fake": d}, log=lambda *a: None)
    return b, d


def test_fader_longe_do_valor_nao_escreve(ponte):
    b, d = ponte
    b.fader(0, 0.9)                      # main esta em 0.5
    b.escoa_uma_vez()
    assert d.valores["main"] == 0.5


def test_fader_assume_ao_cruzar_o_valor(ponte):
    b, d = ponte
    b.fader(0, 0.9)
    b.fader(0, 0.1)                      # cruzou 0.5
    b.escoa_uma_vez()
    assert d.valores["main"] == 0.1


def test_fader_ja_perto_assume_na_hora(ponte):
    b, d = ponte
    b.fader(0, 0.51)
    b.escoa_uma_vez()
    assert d.valores["main"] == 0.51


def test_escoa_aplica_so_a_ultima_posicao(ponte):
    b, d = ponte
    b.fader(0, 0.5)
    for v in (0.6, 0.7, 0.8):
        b.fader(0, v)
    b.escoa_uma_vez()
    assert d.valores["main"] == 0.8


def test_solo_muta_o_grupo_e_devolve(ponte):
    b, d = ponte
    b.solo(5)
    assert d.valores["g1/mute"] == 0.0 and d.valores["g2/mute"] == 1.0
    assert d.valores["main/mute"] == 0.0        # saida nao entra no solo
    b.solo(5)
    assert d.valores["g2/mute"] == 0.0


def test_solo_de_saida_zera_quem_nao_tem_mute(ponte):
    b, d = ponte
    b.solo(1)
    assert d.valores["fone"] == 0.0
    b.solo(1)
    assert d.valores["fone"] == 0.4             # devolvido como estava


def test_mute_sem_parametro_zera_e_devolve(ponte):
    b, d = ponte
    b.mute(2)
    assert d.valores["fone"] == 0.0
    b.mute(2)
    assert d.valores["fone"] == 0.4


def test_botoes_de_banco(ponte):
    b, _ = ponte
    b.on_midi(mido.Message("note_on", note=mackie.BANK_RIGHT, velocity=127))
    assert b.bank.name == "mac"
    b.on_midi(mido.Message("note_on", note=mackie.ARROW_LEFT, velocity=127))
    assert b.bank.name == "rig"
    b.on_midi(mido.Message("note_on", note=mackie.SELECT + 1, velocity=127))
    assert b.bank.name == "mac"


def test_trocar_de_banco_exige_takeover_de_novo(ponte):
    b, d = ponte
    b.fader(0, 0.51)
    b.escoa_uma_vez()
    b.troca_banco(+1)
    b.troca_banco(-1)
    b.fader(0, 0.95)
    b.escoa_uma_vez()
    assert d.valores["main"] == 0.51


def test_rec_carrega_cena_e_marca_a_ativa(ponte):
    b, d = ponte
    b.on_midi(mido.Message("note_on", note=mackie.REC + 1, velocity=127))
    assert d.carregou == "OUTRA" and b.cena_ativa == 2


def test_cena_inexistente_nao_derruba(ponte):
    b, _ = ponte
    b.on_midi(mido.Message("note_on", note=mackie.REC + 5, velocity=127))
    assert b.cena_ativa is None


def test_fader_sem_destino_e_ignorado(ponte):
    b, _ = ponte
    b.fader(7, 0.5)
    b.escoa_uma_vez()          # nao pode estourar


def test_escrita_que_falha_nao_derruba_o_solo():
    class Ruim(FakeDriver):
        def toggle(self, target):
            if target == "g2/mute":
                raise RuntimeError("o daemon nao confirmou")
            return super().toggle(target)

    d = Ruim()
    b = daemon.Bridge(profile.parse_profile(PERFIL), drivers={"fake": d},
                      log=lambda *a: None)
    b.solo(5)
    assert b.solo_ativo == 5            # seguiu em frente apesar do erro


def test_empurra_estado_manda_posicao_e_leds(ponte):
    b, _ = ponte
    enviados = []
    b.enviar = lambda **k: enviados.append(k)
    b.empurra_estado()
    assert any(k["type"] == "pitchwheel" for k in enviados)
    seleciona = [k for k in enviados
                 if k["type"] == "note_on" and k["note"] == mackie.SELECT]
    assert seleciona and seleciona[0]["velocity"] == mackie.ON
