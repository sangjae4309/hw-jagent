---
name: jagent-bottleneck
description: "Analyze existing generated RTL and hardware-emulation profiles/waveforms, reconcile bottlenecks and route results into affected block memories without launching experiments."
---

# Hw Bottleneck


Read .agent/system/policies/ANALYSIS.md and EXPERIMENTS.md. Establish exact source,
build, tool, fixture, clock, timing boundary and authorized artifact directory.
If the run is unspecified, ask for that path; never scan all sim folders.

1. Delegate independent static inspection to rtl-analyst and dynamic inspection
   to hw-emu-analyst when the current task/skill permits. State each exact artifact
   scope and output assignment. Use serial roles if spawning is unavailable.
2. Preserve quantitative evidence with $jagent-experiment's record-only path. Do not
   launch verification. A WDB needs a supported reader/export; report when absent.
   Do not add overlapping inclusive/parallel times or call a potential stall observed.
3. Delegate reconciliation to evidence-integrator. Require matching build identity;
   keep disagreements explicit. Distinguish observations, inference and hypotheses.
   Rank changes by measured non-overlapping budget and correctness/resource risks.
4. Create a finding JSON using .agent/system/templates/finding.json. Run
   `python3 .agent/system/agentctl.py finding publish --file <finding.json>`.
   This writes one canonical finding and reference-only inboxes for affected blocks.
5. Through the parent dispatch each block-<id> owner to inspect its inbox/evidence.
   Each owner runs `finding ack <finding-id> --block <id> --decision accept --note "..."`
   (or reject/defer), then updates its own current design/next-check summary.
   Delivering a file alone does not spawn or notify a background agent.
6. Report the bottleneck, evidence, uncertainty, proposals and per-block receipts.
   Unacknowledged or deferred delivery is pending, not completed knowledge transfer.
   A new design requires a separately authorized verification experiment.

Before recommendations, read both code-style and code-pitfall indexes and applicable notes.
