# mvave via subagents, not an enabled plugin (idea, 2026-09-30)

**Problem:** enabling the `mvave` plugin at user scope loads its skill into every Claude session,
which costs tokens even when the MK-300 is not the subject.

**Idea:** keep the plugin disabled. The MK-300 knowledge is loaded only inside the subagents that
need it; the main session carries only their one-line descriptions.
- `timbrar` and `rig-doctor` (`~/.claude/agents/`) already list this repo. They read
  `skills/mvave/SKILL.md` from the repo when the task touches the MK-300.
- Split into groups when an agent gets too broad (candidates: presets/models, NAM/IR upload,
  globals + doctor).

**Open:** which groups; whether `timbrar`/`rig-doctor` get an explicit "read SKILL.md" line, or a
dedicated `mvave` agent is created.
