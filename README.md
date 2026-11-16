# Portable Codex hardware environment

Reusable Codex skills, specialist agents, engineering rules, and per-project
memory for hardware work. Version **0.2.0**.

Keep this source checkout separate from your hardware project. Each installation
starts with empty project memory; no hardware design or project history is bundled.

## Install or update

Requires Bash and Python 3.8+; Python 3.11+ enables full TOML validation.
Install Codex and hardware tools separately.

Run from your hardware project's root:

```bash
# Preview, then install
bash /path/to/environment/install.sh "$PWD" --dry-run
bash /path/to/environment/install.sh "$PWD"

# Update an existing installation
bash /path/to/environment/install.sh "$PWD" --update
```

Restart Codex after installation or updates. Updates preserve project memory and
registered block agents, and stop on conflicting local edits to managed files.
No installation or update backups are created.

If the project already has another agent system, installation stages transfer
tooling first. Follow the transfer instructions below.

## Skills

In the Codex conversation, type `$jagent-` to find the eight main workflows.
These are Codex skills, not shell commands.

| Skill | Purpose |
| --- | --- |
| `$jagent-transfer` | Replace an existing agent system after review |
| `$jagent-block-scan` | Propose block boundaries and create approved owners |
| `$jagent-block-add` | Add one specified block owner without a full scan |
| `$jagent-bottleneck` | Analyze RTL and waveform evidence with owner feedback |
| `$jagent-experiment` | Record results or run an explicitly authorized stage |
| `$jagent-memory-sync` | Recall and reconcile project and block memory |
| `$jagent-env-promote` | Propose a portable improvement to this source |
| `$jagent-grill` | Resolve design decisions and capture terms and ADRs |

The interview helpers `$grilling` and `$domain-modeling` keep their names.

Example:

```text
$jagent-block-add Add an owner for src/packet_filter.cpp, with shared read
access to include/packet.h, using the HLS rules.
```

## Transfer an existing agent system

Run the installer, then invoke `$jagent-transfer`. Staging leaves the existing
root `AGENTS.md` and other controls active until you approve the exact plan.

The approved transfer:

- Removes or replaces inventoried root/nested agent instructions, roles, skills,
  and repository-local agent configuration, including `AGENTS.md`.
- Moves useful history into `.agent/memory/history/` or integrates it into
  canonical memory, then deletes the old copies. Discarding knowledge requires
  separate acknowledgement; unrelated project documents may be retained.
- Removes inventoried `.agent/backups/`, staging files, and the transfer plan.
- Preserves source code, fixtures, unrelated tests/documents, and global settings.

**There is no backup or rollback.** Transfer is not atomic across files, so an
interruption can leave partial changes. Review the deletion and knowledge
relocation scope before approving. After transfer, restart Codex, run doctor,
and review moved references using `.agent/memory/migration-map.json`.

See the [transfer skill](skills/jagent-transfer/SKILL.md) for the detailed flow.

## Agents and project memory

| Agent | Responsibility |
| --- | --- |
| `hw-runner` | Explicitly authorized hardware runs and evidence records |
| `rtl-analyst` | Generated RTL, schedules, and static hypotheses |
| `hw-emu-analyst` | Matching waveform/profile evidence and dynamic stalls |
| `evidence-integrator` | Reconcile findings and route feedback to owners |
| `env-curator` | Generalize selected lessons into this separate source |
| `block-<id>` | Own a project's approved block and its memory |

Installed files live in:

```text
AGENTS.md          Project instructions
.agents/skills/    Codex skills
.codex/agents/     Specialist and block agents
.agent/rules/      Engineering styles and pitfalls
.agent/system/     CLI, policies, and templates
.agent/memory/     Project, agent, block, experiment, finding, and history records
```

Memory is an explicit file convention. Agents are invoked by the parent session;
they are not background daemons. Hardware runs require current authorization and
an inspected project runner. Recorded evidence distinguishes measured results
from hypotheses; missing measurements remain unknown.

## Check and maintain

From an installed project's root:

```bash
python3 .agent/system/agentctl.py doctor
python3 .agent/system/agentctl.py --help
```

Doctor checks repository-local files, schemas, ownership, and evidence. It does
not run Codex or hardware tools, or inspect global plugins.

Use `$jagent-env-promote` to propose a reusable lesson. The installer records this
source's location in `.agent/upstream.local.json`. Rebind it after moving the source:

```bash
python3 .agent/system/agentctl.py upstream set --path /path/to/environment
```

Promotion requires review and approval of the exact external diff. It does not
commit, push, export project history, or update other projects automatically.
See the [promotion policy](policies/PROMOTION.md).

Source folders: `agents/`, `skills/`, `general/`, `policies/`, `templates/`, and
`tools/`. Follow [AGENTS.md](AGENTS.md) when editing this reusable source.
Licensing is covered by [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
