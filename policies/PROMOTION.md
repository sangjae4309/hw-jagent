# Promotion into the external environment

The installed project is not the source of portable rules. The source is a separate
checkout, resolved from CODEX_ENV_HOME or .agent/upstream.local.json. The local
binding is ignored by Git and is recreated on another machine. Do not hard-code
an environment repository name or search private directories for a likely match.

The env-curator handles style, pitfall, agent and policy proposals. Use
.agent/system/templates/promotion.json as the draft schema. Supporting evidence
stays local; only curated edits under source general/, agents/ or policies/ leave
the project. No automatic bulk memory export, source-code copy or block-role copy.

A style is a preference; a pitfall explains a failure mechanism and its limits;
a general agent is a reusable job description without a fixed source boundary;
a policy is a cross-project workflow. Keep project results/constraints local.

Read the target files, compare alternatives, and show the exact external diff.
Semantic review is mandatory: the CLI's identifier/path/credential filters are
only guardrails, not proof of anonymization or general applicability. Add known
project names, private symbols and addresses to project_identifiers in the draft.
Keep user decisions and evidence limitations; do not silently upgrade a hypothesis.

promote plan captures hashes of selected local evidence and target source files.
promote apply rechecks both and writes only after approval. It writes no backups,
creates no Git commit/push and never edits other installed projects. A local
metadata receipt records outcomes, not a snapshot of the old source.

Filesystem permission is separate from approval. The parent Codex session must
have access to the external source (for example codex --add-dir /path/to/env).
Agent TOML does not grant that permission. If denied, keep the local proposal and
report the exact blocked operation; never weaken the sandbox.

Distribute accepted source changes by running that source's install.sh --update
in selected projects. Resolve conflicts rather than overwriting local edits.
