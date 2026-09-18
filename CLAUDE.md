# mvave

## Every change is committed AND pushed
Any change to this repo ends with `git commit` + `git push` to `origin/main` in the same turn —
never leave work only in the working tree or only in a local commit.
**Why:** João installs the plugin and the CLI from GitHub (`claude plugin marketplace add jpfaria/mvave`,
`pip install git+…`); an unpushed fix does not exist for him or for his other sessions.
**How to apply:** run the tests (`python3 -m pytest -q`, check the exit code, not a piped `tail`),
commit, push, and say the commit hash. Docs generated from code (`python3 tools/build_reference.py`)
are regenerated and included in the same commit.
