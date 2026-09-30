# mvave via subagents, not an enabled plugin (idea, 2026-09-30)

**Problem:** enabling the `mvave` plugin at user scope loads its skill into every Claude session,
which costs tokens even when the MK-300 is not the subject.

**Decision:** plugin stays disabled; small subagents in `agents/`, symlinked into
`~/.claude/agents/` (only their one-line descriptions sit in every session). Each one reads the
parts of `skills/mvave/SKILL.md` it needs, so the knowledge stays in one place.

| agent | scope |
|---|---|
| `mk300-preset` | show/load/model/param/enable/save/copy |
| `mk300-upload` | NAM A2 / IR into AMP/CAB slots |
| `mk300-catalog` | which model matches real gear; read-only, haiku |
| `mk300-system` | globals, doctor, re-amp, listen, timeouts |

Install: `for a in agents/mk300-*.md; do ln -sf "$PWD/$a" ~/.claude/agents/; done`

## Next idea (2026-09-30): a tree of agents
A user-scope `tone-builder` agent as the entry point, which knows the device agents
(`mk300-*`, OpenRig, Ampero…), and those know the agents that own each plugin/skill.
- Tested: a subagent (`mk300-catalog`) has the Agent tool and launched `mk300-preset`, so nesting works.
- Cost: every level starts a fresh context (~40k tokens measured for an empty "answer OK"),
  so keep the tree shallow (2 levels) and send one complete task per hop.
- The subagent does not see the list of agent types: each agent's prompt must name the agents
  it can call.
