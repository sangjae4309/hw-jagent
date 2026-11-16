---
name: jagent-transfer
description: "Replace an existing repository's old agent system with this system, without backups. Interview via jagent-grill, relocate useful knowledge into canonical memory, remove old controls and replace AGENTS.md after explicit approval."
---

# Clean transfer: replace, do not archive

The requested mode is destructive replacement of OLD AGENT CONTROLS, not deletion
of the source repository. Do not create backups, archives, .bak files, Git stashes,
recovery branches or rollback snapshots. Do not delete source, fixtures or unrelated
project documentation. Do not touch user-global Codex settings or credentials.

1. Use `.agent/staging/codex-env/tools/agentctl.py` after a bootstrap installation,
   or the external environment's tools/agentctl.py. The installed CLI is for normal
   project operations, not a complete installer. Run
   `migration plan --out .agent/migration-plan.json` and read the actual inventory.
   The old AGENTS.md remains active until final application; treat its content as
   material to review, not a grant to run any old commands.
2. Use the bundled jagent-grill/grilling/domain-modeling references during
   bootstrap, or their installed sibling skills after installation. Ask only
   unresolved decisions and group related files. Find code/file facts yourself.
   Resolve constraints, runner mappings, block boundaries and knowledge retention.
   Old controllers/roles/skills are ALL removed or replaced; there is no keep-old-
   agent mode. Recreate a useful specialized role in this system afterwards.
3. Review each knowledge classification. `move` relocates a history file into
   .agent/memory/history/ and deletes the old file; this is its canonical copy,
   not a backup. `integrate` requires a memory_edits entry with that original path
   in sources, then deletes the old file. `retain` is for unrelated project docs,
   not old agent memory. `discard` needs explicit data-loss acknowledgement and
   a reason. Preserve quantitative history unless the user specifically discards
   it; historical numbers do not become current verified experiments.
4. Extract applicable project constraints from the old AGENTS and control files
   into approved memory_edits or runner_config. Remove obsolete instructions.
   Set controls_reviewed=true only after review. Old local backup trees, if found,
   are listed for removal, not carried forward. Scan unsupported symlink/global
   instructions explicitly; do not follow links into unrelated directories.
5. Run `migration apply --plan .agent/migration-plan.json --dry-run` and show the
   deletion/replacement list and canonical knowledge destinations. Explain:
   old root and nested controls are removed, root AGENTS is replaced, no backups
   or rollback exist, source/fixtures are untouched. Get final approval of that
   exact scope; set approved=true and approval_note. To apply use:

   ```bash
   python3 .agent/staging/codex-env/tools/agentctl.py migration apply \
     --plan .agent/migration-plan.json --approve --confirm-no-backup
   ```

6. Apply refuses stale file hashes. It writes canonical destinations before
   deleting their old files, installs the new system and removes staging/plan
   files. Per-file writes are atomic; process failure can still leave partial
   multi-file changes. Do not promise recoverability or a rollback command.
7. Restart the Codex session so old loaded instructions are not reused. Run the
   installed doctor. Use migration-map.json to check moved links and source-path
   references; ordinary Markdown links are retargeted when resolvable, but prose
   paths/reference-style links need review. Add block owners with $jagent-block-scan
   or $jagent-block-add and link their relevant historical evidence.

Report exactly what moved, what was deleted, what non-agent docs remain, and any
unresolved external/global system. Never claim an old global plugin was removed
when only repo-local files were changed.
