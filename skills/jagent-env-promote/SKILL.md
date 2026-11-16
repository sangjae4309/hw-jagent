---
name: jagent-env-promote
description: "Promote a selected local coding rule, pitfall, workflow or reusable agent into the separate original Codex environment source. Use when the user wants a local improvement shared across future projects; delegate to env-curator."
---

# Promote a portable improvement

Read .agent/system/policies/PROMOTION.md. Delegate to env-curator when spawning is
available; otherwise say that the parent is carrying out that role serially.

1. Inspect the selected local evidence. Run
   `python3 .agent/system/agentctl.py upstream show`.
   If the clone moved, use `upstream set --path /actual/source/checkout` only after
   identifying the user's intended source. CODEX_ENV_HOME is another explicit
   source override. Do not infer a repository name or use installed snapshots as
   the source. The target must be outside this project.
2. Classify the improvement: style, pitfall, agent or policy. Compare existing
   general rules/roles. Read both style and pitfall indexes. Reject a project-only
   design, measurement or block-specific ownership as a general rule.
3. Use jagent-grill for unresolved applicability, exceptions and design choices.
   Curate a draft using .agent/system/templates/promotion.json. Evidence paths
   remain local. Put only generalized full-file content in edits. Include any
   known project names/private identifiers in project_identifiers and inspect the
   result manually; a substring filter alone does not prove anonymization.
4. Set reviewed_generalization=true after semantic review. Run:

   ```bash
   python3 .agent/system/agentctl.py promote plan \
     --file .agent/drafts/promotion-draft.json \
     --out .agent/drafts/promotion-plan.json
   ```

   Show the proposed external paths and exact diff. Explain scope and tradeoffs.
   Set approved=true and approval_note only after current user approval.
5. Ensure the parent session can write to the external source; for CLI use, start
   Codex with `--add-dir /path/to/environment` when needed. Do not change sandbox
   policy or attempt privilege escalation. A role definition does not grant access.
6. Preview and apply the SAME plan:

   ```bash
   python3 .agent/system/agentctl.py promote apply \
     --plan .agent/drafts/promotion-plan.json --dry-run
   python3 .agent/system/agentctl.py promote apply \
     --plan .agent/drafts/promotion-plan.json --approve
   ```

   The CLI checks target and evidence hashes and approved content. It does not
   commit, push, make backups, or update other projects. Report the external diff
   and local metadata receipt. Use the source install.sh --update in selected
   projects to adopt the change. Do not overwrite local memory during distribution.
