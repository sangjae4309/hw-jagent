# Shared failure checks

## Historical evidence is not current verification

A passing old artifact verifies that artifact's source, input, settings and stage;
it does not prove the current worktree or a later board image. Confirm identities
before reusing results. Missing cycles/area are unknown, not zero. Preserve failure
and timeout evidence. A later passing build is not a controlled single-change A/B.

## Source intent is not observed hardware

An UNROLL/PIPELINE/ALLOCATION directive expresses intent. Verify achieved II,
instances, memories and the dependency path in actual generated reports/RTL.
Do not sum overlapping block intervals as elapsed time or treat emulator wall time
as hardware cycles. Dynamic stall claims need matching waveform/profile evidence.

## Fixes need a scope and a disproof check

Record a hypothesis separately from observation. Keep alternative explanations
until discriminating evidence rules them out. An accepted design suggestion remains
unverified until a separately authorized run measures the changed design.
Do not weaken arithmetic precision, fixtures or tolerances to manufacture a pass.
