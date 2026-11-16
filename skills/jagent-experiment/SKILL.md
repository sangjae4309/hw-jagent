---
name: jagent-experiment
description: "Run an explicitly authorized hardware verification stage and preserve cycles, II, resource/timing and correctness evidence. Also use to record existing results; this skill does not itself authorize any build."
---

# Hw Experiment


Read WORKFLOW.md and EXPERIMENTS.md under .agent/system/policies/. Check current
stage authorization, source/input freeze, exact runner and output scope. With
permission delegate execution to hw-runner; otherwise only inspect supplied results.
Do not bypass approved runners, change tolerances or destroy the previous run.

Use `python3 .agent/system/agentctl.py experiment draft <id> --block <id> --stage csynth`
(or the actual stage) to create a JSON draft. Fill source, config, numerical_status,
status, summary, metrics and evidence from inspected artifacts. Do not report
placeholder nulls as measured numbers. Read .agent/system/templates/experiment.json
for metric/evidence fields. Add all relevant clock/configuration/input conditions.
Use csynth estimates, simulated values and board measurements with correct kind
and scope. Record failed/timeout attempts and what remains unknown.

Use `experiment record --file <draft.json>` to freeze the record and copy small
explicit evidence files outside resetting build folders. External evidence needs
an exact approved path or durable URI, SHA-256 and retention note; no automatic
cloud upload occurs. Large waveforms are not silently copied into Git.
Use `experiment compare <old-id> <new-id>` for matched-condition checks. Do not
claim speedup when it reports unpaired. Corrections use a new ID with supersedes.
Publish material interpretation through $jagent-bottleneck or $jagent-memory-sync.

Before recommendations, read both code-style and code-pitfall indexes and applicable notes.
