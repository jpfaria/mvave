---
tags: [mvave, learnings]
created: 2026-09-18
updated: 2026-09-20
source: claude-code-sessions
---

# mvave — Learnings

## 2026-09-18 — One direct-reference URL per package across sibling repos

- **Gotcha / invariant:** `tone-analyzer` is a `git+https://…` direct reference. If two packages in the same environment (e.g. `mvave` and `tone-builder`) point at it with different URLs (one pinned `@vX`, one unpinned), pip refuses to resolve. Keep the exact same URL string in every sibling repo (`53df8dc`).
- **Why it matters:** installing the whole toolchain fails, not just this package.
- **Applies to:** `pyproject.toml` `dependencies`, and every other repo that depends on `tone-analyzer`.

## 2026-09-20 — USB Audio is borrowed state; restore it or the rig goes silent

- **Incident:** 19–20/09, `mvave reamp` (called from tone-builder) left the MK-300's global
  `usb-audio` at `2 (RESAMPLE)`. In that mode the pedal ignores the guitar input and processes
  USB playback instead, so the rig was silent and João lost an hour debugging it before
  `mvave global` surfaced `usb-audio 0x3d = 2 (RESAMPLE)`. Same class of bug hit the Ampero in
  another repo.
- **Gotcha / invariant:** any code path that switches `usb-audio` (re-amp today, maybe more
  later) borrows it and must restore it — on normal completion, on exception, and on
  SIGINT/SIGTERM before the process dies. The guarantee lives in code, not in a caller
  remembering to clean up: `mvave.usb_audio.borrowed_usb_audio(device)` is the single choke
  point allowed to write that field (`mvave/usb_audio.py`); `reamp()` uses it and does not touch
  `device.set_u8` for that field itself (see `tests/test_reamp.py::test_reamp_goes_through_borrowed_usb_audio`,
  a regression guard that fails if a future edit bypasses the helper).
  - If the restore write itself fails (e.g. MIDI timeout), it does not raise — it prints a loud
    warning to stderr with the exact fix (`mvave global-set usb-audio 0`), so it never masks
    whatever the caller was doing.
  - `mvave doctor` (`mvave/doctor.py`, pure `diagnose(profile, globals_bytes)`) is the
    independent sanity check: reads the globals and reports `usb-audio != ON` (or any future
    similar field) with the fix, exit 1 when dirty.
- **Why it matters:** a pedal silent to the guitar input looks like a hardware or OBS problem,
  not a leftover global field — costs real debugging time (measure before hypothesizing, see
  `~/Documents/Obsidian/music-setup/`).
- **Applies to:** `mvave/reamp.py`, `mvave/usb_audio.py`, `mvave/doctor.py`, and any future
  command that needs USB Audio in a non-ON mode.

## 2026-09-20 — The MK-300 is AM4 and imports NAM (not AM3)

- **Fact (João):** his MK-300 is the AM4 generation and now accepts `.nam` directly.
- **Evidence in the editor (M-EFCS, `App.framework` strings, read-only):** `.am4Data`,
  `convertNamToAm4Data`, `calc_bias_gru_am4` (AM4 looks like a GRU), `mk300_am4_preset.bin` /
  `mk300_am4_ampCab.bin` next to the `am3` ones; NAM conversion UI strings (`namConvertingHashing`,
  `…Uploading`, `…Querying`) and the endpoints `community.m-vave.com/bbs/api/namhash` and
  `/uploadnam`; a "Switch to TONE3000" community link.
- **Observed on the pedal:** preset `[105] nam` uses AMP index 119 (`120GKL800_BS`). Inference, not
  confirmed with João: his NAM import sits in that factory bass slot, i.e. imports replace catalog
  slots and `mvave` keeps printing the catalog name.
- **Not measured yet:** the SysEx the editor sends on import, whether conversion is local or on
  M-VAVE's server, which AMP/DS slots are writable. João does not want `mvave` calling M-VAVE's API.
- **Applies to:** any upload/import feature; `docs/protocol.md` "not covered".
