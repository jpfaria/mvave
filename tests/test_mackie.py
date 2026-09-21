import mido

from mvave import mackie


def test_fader_is_unsigned_14_bit():
    f = mackie.decode(mido.Message("pitchwheel", channel=2, pitch=8191))
    assert isinstance(f, mackie.Fader) and f.channel == 2
    assert f.value == 1.0
    assert mackie.decode(mido.Message("pitchwheel", channel=0, pitch=-8192)).value == 0.0


def test_encoder_is_relative():
    right = mackie.decode(mido.Message("control_change", control=0x10, value=1))
    left = mackie.decode(mido.Message("control_change", control=0x17, value=0x41))
    assert (right.channel, right.delta) == (0, 1)
    assert (left.channel, left.delta) == (7, -1)


def test_button_kinds_and_channel():
    b = mackie.decode(mido.Message("note_on", note=mackie.MUTE + 4, velocity=127))
    assert (b.kind, b.channel, b.pressed) == ("mute", 4, True)
    bank = mackie.decode(mido.Message("note_on", note=mackie.BANK_RIGHT, velocity=127))
    assert (bank.kind, bank.channel) == ("bank_right", None)
    assert mackie.decode(mido.Message("note_off", note=mackie.SOLO, velocity=0)).pressed is False


def test_round_trip_of_a_fader_position():
    kwargs = mackie.fader_position(3, 0.5)
    back = mackie.decode(mido.Message(**kwargs))
    assert back.channel == 3 and abs(back.value - 0.5) < 1e-4


def test_led_kwargs_build_a_valid_message():
    assert mido.Message(**mackie.led(mackie.SELECT + 1, True)).velocity == 127
    assert mido.Message(**mackie.led(mackie.SELECT + 1, False)).velocity == 0
