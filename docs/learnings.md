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

## 2026-09-20 — A NAM capture is the amp alone: CAB off is the fizz

- **Symptom:** "coloquei um NAM na mk300 e ta fazendo um barulho horrivel". Measured on preset
  `[105] nam`: `CAB` was **off**. A NAM capture models the amp, not the cabinet, so a raw amp into
  an FRFR speaker is exactly that fizz. `usb-audio = ON` and `rch = Nor` were ruled out first.
- **Gotcha / invariant:** before blaming the capture or the routing, read the CAB block. CAB off is
  only correct when the chain feeds a real power amp + cab (the SYN-5050 path), never FRFR.
- **Do not read the CAB catalog names as instrument hints:** `1AC-SeVin` is **Vox AC**
  (Celestion/Alnico), a guitar cab — not an acoustic one. CAB indices 1–64 are all guitar cabs
  (`docs/catalog.md`). Claude called it an acoustic cab and swapped João's choice on that basis.
- **Applies to:** any "horrible noise" report on the MK-300, and any code or advice that maps a
  catalog name to a use case.

## 2026-09-20 — Firmware V73: native NAM A2 (A2-Lite), no conversion

- **Official release note** (`MK300.txt` on m-vave.com/appdownload), V73, 2026-09-07: "Added Native
  support for NAM A2 models", 12 new white-box DS models, Input Gain, USB Rec Level mode, Comb Key;
  the update resets the globals. AM4 came in V63; V67 fixed AM4 Reso/Pres/Bright (neutral =
  Reso 0, Pres 50, Bright 100).
- **NAM A2 (TONE3000 guide):** one A2 `.nam` is a slimmable network holding A2-Full (8 channels,
  DAW) and A2-Lite (3 channels, embedded; ~50% of a 600 MHz Cortex-M7). The device picks the width;
  the MK-300 runs A2-Lite. No separate "lite" download exists.
- **TONE3000 API** (`api.tone3000.com/rest/v1`, public anon key, same one as
  `OpenRig-plugins/scripts/check_updates.py`): `tones` (`title`, `gear`, `platform`, …) and `models`
  (`tone_id`, `name`, `model_url`, `architecture_version`, `size`). A2 = `architecture_version = "2"`
  (`size` is null there), file `<hash>_a2.nam`. No M-VAVE platform exists there and none is needed.
- **Stale sources to ignore:** posts telling you to convert `.nam` → `am3data` with SincoANN, and the
  editor strings `namhash` / `uploadnam` / `convertNamToAm4Data` (the pre-V73 conversion path).
  João does not want `mvave` calling M-VAVE's API.
- **Observed on the pedal:** preset `[105] nam` uses AMP index 119 (`120GKL800_BS`) — inference, not
  confirmed: his NAM import sits in that slot and `mvave` prints the catalog name.
- **Editor support for A2 (2026-09-20):** the App Store listing (id 6470352068) says 3.9.0721,
  2026-09-11, "Added A2 Lite support" — that is the iOS build. The **macOS** build on João's Mac App
  Store is still 3.7.141x (July), with no A2 strings in it. M-VAVE ships no Mac build outside the
  App Store: the site's "PC" download is a Windows-only zip (`m_efcs.exe`), plus the Android APK.
  So today a `.nam` goes into the pedal from the phone app or Windows, not from the Mac editor —
  and the Mac editor cannot be spied on for the upload SysEx until it updates.
- **Not measured yet:** the SysEx the editor sends when it loads a `.nam`, and which AMP/DS slots
  are writable. No public doc covers it (M-VAVE only publishes a video: "NAM A2 introduction,
  loading, and listening").
- **Sources:** m-vave.com/appdownload; tone3000.com/guides/nam-a2-the-complete-guide;
  tone3000.com/blog/introducing-neural-amp-modeler-nam-architecture-2-a2.
