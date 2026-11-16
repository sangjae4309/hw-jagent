---
name: jagent-block-scan
description: "Discover hardware block ownership and generate project-local Codex block agents with separate memories. Use for a new hardware project or new block boundaries; accept jagent_block_scan as a natural-language alias."
---

# Hw Block Scan


1. Read root AGENTS.md, .agent/blocks.json, project architecture and applicable
   style AND code-pitfall indexes. For a single named block prefer $jagent-block-add. Run `python3 .agent/system/agentctl.py block scan --out .agent/block-plan.json`.
   This is a lexical candidate scan, not a verified hardware partition. Inspect
   source interfaces, build targets and existing ownership to refine candidates.
2. Invoke [jagent-grill](../jagent-grill/SKILL.md) and its two companions.
   Ask decisions in dependency order: variants vs blocks, ownership boundaries,
   shared files, interfaces, dependencies, source roots and relevant style profiles.
   Discover facts yourself; do not ask the user to list files you can inspect.
   Do not create agents just because a directory or function exists.
3. Edit the plan's blocks to confirmed boundaries. Each block has id, description,
   owned_paths, shared_read_paths, dependencies, interfaces and style_profiles.
   There must be one writer per owned path. If two blocks share a translation unit,
   choose one owner and shared reads or ask to change the boundary; do not silently
   split source or assign concurrent writers. Reject dependencies on missing IDs.
4. Present the final map. Only after confirmation set approved=true, record
   approval_note, and run `block apply --plan .agent/block-plan.json --approve`.
   It creates native .codex/agents/block-<id>.toml and .agent/memory/blocks/<id>/.
   Existing block memories are never overwritten by a rescan.
5. Inspect generated files, populate MEMORY.md from current source with locators,
   linking relevant .agent/memory/history/ evidence and applicable pitfalls,
   leaving unknown performance null/unverified. Run doctor. Do not run hardware
   checks. Restart Codex if new roles are not visible. Report pending boundaries.
