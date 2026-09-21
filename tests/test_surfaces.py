from mvave import surfaces


def test_default_surface_is_the_smc_mixer():
    s = surfaces.get()
    assert s.name == "SMC-Mixer" and s.faders == 8 and s.encoders == 8
    assert s.port_hint == "SMC-Mixer-Master"


def test_name_is_normalised():
    assert surfaces.get("smc_mixer") is surfaces.get("SMC-MIXER")


def test_unknown_surface_is_refused():
    try:
        surfaces.get("nope")
    except SystemExit as e:
        assert "unknown surface" in str(e)
    else:
        raise AssertionError("should have refused")
