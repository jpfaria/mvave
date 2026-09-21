# Bridge: a surface driving other gear

`mvave bridge PERFIL.yaml` reads a control surface (today the SMC-Mixer) and
writes to whatever the profile says — the surface never knows what it controls.

```
superficie (Mackie)  ->  Bridge  ->  driver  ->  aparelho
```

## Drivers

| Driver | Talks to |
|---|---|
| `hd8` | PreSonus Quantum HD 8, through the `quantum-hd8` lib (UCNet). The HD 8 **does not receive MIDI**: a sweep of CC, pitch bend and notes on both of its ports changed none of its 1419 parameters (2026-09-20). |
| `mac` | macOS output volume. Unsupported when the default output is an audio interface — AppleScript answers `missing value` because the volume lives in the interface. |
| `app` | One application's own volume (`Spotify`, …). |

A driver that cannot do something raises `Unsupported`; the bridge logs it and
carries on. One channel the daemon refuses must never abort a solo — that bug
cost an evening on 21/09.

## Profile

```yaml
surface: smc-mixer
banks:
  - name: HD 8
    faders:
      1: {driver: hd8, target: global/mainOutVolume, label: MAIN, group: out, mute: global/mute}
      5: {driver: hd8, target: line/ch1/volume, label: GUITA 1, group: in, mute: line/ch1/mute}
    buttons: {rec: scene, select: bank}
```

- `group` (`in`/`out`) is what keeps **solo** honest: soloing an input mutes the
  other inputs and leaves the outputs alone.
- A fader **without** `mute:` is silenced by zeroing its own value, which is then
  remembered and given back — the HD 8 has no mute for the headphone outputs.
- `rec: scene` makes R n load the n-th scene of that fader's driver;
  `select: bank` makes □ n pick bank n. Channel ◀/▶ and the arrows page banks.

## Feedback

On every bank change, scene load, mute and solo the bridge pushes the state
back: each fader's real value (Pitch Bend) and the LEDs of mute, solo, the
loaded scene (R) and the active bank (□).
