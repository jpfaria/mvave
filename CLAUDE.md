# mvave

## Every change is committed AND pushed
Any change to this repo ends with `git commit` + `git push` to `origin/main` in the same turn —
never leave work only in the working tree or only in a local commit.
**Why:** João installs the plugin and the CLI from GitHub (`claude plugin marketplace add jpfaria/mvave`,
`pip install git+…`); an unpushed fix does not exist for him or for his other sessions.
**How to apply:** run the tests (`python3 -m pytest -q`, check the exit code, not a piped `tail`),
commit, push, and say the commit hash. Docs generated from code (`python3 tools/build_reference.py`)
are regenerated and included in the same commit.

## The MK-300 runs NAM A2 natively (firmware V73) — no conversion
Since firmware **V73 (2026-09-07)** the MK-300 has "Native support for NAM A2 models" (official release
note). A TONE3000 **A2** `.nam` is ONE file that holds both A2-Full (8 ch) and **A2-Lite** (3 ch); the
pedal runs the **A2-Lite** width. It is a real NAM running on the pedal, **not** converted to
AM3/AM4. AM4 (since V63) is M-VAVE's own format and still exists next to it.
**Why:** (2026-09-20) from stale `.am3Data` wording in this repo and old web posts (SincoANN
`.nam` → `am3data`) I told João three times that the pedal "only accepts AM3" and that NAM had to be
converted through M-VAVE's cloud. He had to order me to go read the docs.
**How to apply:** amp/drive loading = "pick an **A2** capture on TONE3000 (`<hash>_a2.nam`,
`architecture_version = 2`), send the `.nam` as is". Never propose a conversion step or M-VAVE's API.
A1-only captures are not covered by the V73 note. Gear facts older than the current firmware are
suspect: read `docs/learnings.md` and the release note
(`https://yms-file-store.oss-cn-hongkong.aliyuncs.com/software/releaseNote/firmware/MK300.txt`)
before asserting what the pedal can do. When João's word and a doc disagree about his gear, his word
wins and the doc gets fixed in the same commit.
