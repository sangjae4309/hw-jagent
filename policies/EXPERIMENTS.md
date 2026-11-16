# Hardware evidence contract

Record every material experiment, including failures, with a stable ID. Separate
requested structure from observed generated structure and simulation/runtime.
A result needs source revision or content digest, dirty-tree state, build config,
tool/version, device/board, variant, precision, clock/domain, input identity,
shape/workload, stage, numerical status and exact measurement boundary.
A draft has nulls until evidence fills them. Metrics with no evidence remain null.

## Stages are not interchangeable
- csynth: schedule/latency/II/resource and clock estimates, not measured runtime.
- rtl_sim or hw_emu: simulated cycles/time for a defined waveform/profile interval.
- implementation: mapped/routed utilization and timing; distinguish synthesis
  from placement and routing. WNS/TNS need their actual report and clock constraints.
- board: measured device execution under recorded hardware/software conditions.
- csim: functional C-model results; no physical parallelism proof.

For area report resource type and unit: LUT, FF, DSP, BRAM18/BRAM36, URAM. Do not
conflate counts, percentages, bits, sites or cells. Keep BRAM18 and BRAM36 separate.
For latency distinguish per-invocation, per-input, full-batch, kernel-only, host
end-to-end and emulator wall time. A requested II is not achieved II. An unknown
or data-dependent csynth latency is not a fixed cycle count.

Use one record per build/run/measurement scope. Correction creates a new record
with supersedes=<old-id>; never overwrite or delete the old record. Keep copied
small evidence beside the record with SHA-256. Large waveforms may remain in an
explicit external artifact store, with digest and retention note. A path alone is
not durable retention. No automatic upload or cloud credentials are supplied.

Comparisons require identical stage, tool/version, device, precision, clock,
workload, input hash, shape, and relevant configuration. Different design variants
may be compared, but changed inputs or unknown settings invalidate paired claims.
Metric units, scope, method and clock domain must also match. Retain raw ratios
as artifact comparisons when unmatched; do not call them architectural speedup.
A result can be useful with incomplete provenance but cannot pass matched gating.
