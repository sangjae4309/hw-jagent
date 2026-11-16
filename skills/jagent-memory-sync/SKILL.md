---
name: jagent-memory-sync
description: "Recall, reconcile and update project or block memory after material work, retaining historical experiments and avoiding duplicated facts. Use for context recovery, stale-memory reviews and durable design lessons."
---

# Memory Sync


Read .agent/system/policies/MEMORY.md and the memory index. Search existing memory
with `python3 .agent/system/agentctl.py memory search <query>`. Inspect the current
source, owner registry and source fingerprints before reusing old conclusions.

Update the canonical project or assigned block summary, not every agent file.
Keep exact results in immutable experiment records and findings. Record failed
alternatives with evidence; replace stale current state rather than append mutually
contradictory facts. Unknown and unverified claims must remain labeled.

For feedback, dispatch block owners to inspect inboxes and use finding ack. For
substantial source changes, use block refresh --block <id> --note "review scope"
only AFTER reviewing the code; a refreshed timestamp is not verification evidence.
Capture terms/ADRs with domain-modeling, keeping decisions and metrics separate.
Use canonical history/ and migration-map.json after transfer. Read applicable
code-pitfall notes before proposing another design. Do not turn old instructions
into active rules. Use env-curator for reviewed portable lessons, not bulk exports. Do not run hardware checks or publish externally.
Run doctor and report unresolved ownership, stale evidence and pending receipts.
