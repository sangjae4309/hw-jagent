---
name: jagent-block-add
description: "Add exactly one user-selected hardware block owner and its separate memory without a repository-wide scan. Use when the user names a block or source path, says add a block agent, or uses jagent_block_add."
---

# Add one block owner

1. Read root AGENTS.md, .agent/blocks.json, both code-style and code-pitfall
   indexes, project constraints and only the nominated block's source/interfaces.
   Do not run the full block scan. Find file facts yourself; do not ask again for
   facts or decisions the user already supplied.
2. Use jagent-grill to resolve only missing boundaries: owned vs shared files,
   interfaces, dependencies, implementation variants and relevant style profiles.
   One file/directory has one writer. Stop on overlapping ownership; ask whether
   to keep the current owner or explicitly revise the boundary in a separate task.
3. Draft a single block, for example:

   ```bash
   python3 .agent/system/agentctl.py block add packet-filter \
     --description "Own the packet filtering datapath" \
     --path src/packet_filter.cpp --profile hls \
     --out .agent/block-plan.json
   ```

   Add --shared-path, --depends-on and --interface only for inspected/confirmed
   values. The CLI drafts; it does not silently approve or scan. A source path
   must already exist; creating a new design scaffold needs a separate assignment.
4. Present the one-block scope. When the user's instruction already explicitly
   confirms all these choices, use it as the approval; otherwise ask once.
   Set approved=true, approval_note and blocks[0].approved_boundary=true.
   Run `block apply --plan .agent/block-plan.json --approve`.
5. Inspect .codex/agents/block-<id>.toml and populate
   .agent/memory/blocks/<id>/MEMORY.md from actual source and relevant historical
   evidence. Include interfaces, state, range assumptions, pitfalls, unknown
   performance and next-design checks. Do not invent numbers or run hardware jobs.
   Run doctor. Report that other block agents and memories were left unchanged.

The owner reads its own memory/inbox and applicable style/pitfall notes on every
new design task. Reload/restart Codex if its new role is not yet visible.
