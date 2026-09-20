# mvave

## Every change is committed AND pushed
Any change to this repo ends with `git commit` + `git push` to `origin/main` in the same turn —
never leave work only in the working tree or only in a local commit.
**Why:** João installs the plugin and the CLI from GitHub (`claude plugin marketplace add jpfaria/mvave`,
`pip install git+…`); an unpushed fix does not exist for him or for his other sessions.
**How to apply:** run the tests (`python3 -m pytest -q`, check the exit code, not a piped `tail`),
commit, push, and say the commit hash. Docs generated from code (`python3 tools/build_reference.py`)
are regenerated and included in the same commit.

## The MK-300 is AM4 and imports NAM
João's MK-300 is the **AM4** generation and **accepts `.nam` files** (M-EFCS Import page). Never say
"the MK-300 only takes AM3" or treat `.am3Data` as its format.
**Why:** (2026-09-20) the repo docs still said `.am3Data`, and from that and 6 KB `.am3Data` files in
iCloud I told João the pedal "only accepts AM3" and built a plan around a NAM→AM3 cloud conversion.
He had already said it: "mk-300 é am4 e AGORA ACEITA NAM".
**How to apply:** anything about loading amps/drives starts from "NAM goes in". The editor ships both
`mk300_am3_*` and `mk300_am4_*` assets and a `convertNamToAm4Data` routine; `.am3Data` files are for
the older generation. What is still unmeasured: the upload SysEx and which slots are writable
(`docs/learnings.md`). When João's word and an old doc disagree about his gear, his word wins and the
doc gets fixed in the same commit.
