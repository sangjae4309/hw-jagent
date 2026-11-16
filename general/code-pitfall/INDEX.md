# Code-pitfall routing

Read this index and common.md before design, code review or a performance change.
Read only relevant domain notes. Block owners, RTL analysts, waveform analysts,
the evidence integrator and the environment curator all follow this routing.

| Work | Required notes |
| --- | --- |
| Any design/change or result interpretation | common.md |
| HLS addresses, index widths, counters, signedness | hls-signed-index.md |
| HLS recurrences, partitioning, reduction and instance reuse | hls-scheduling.md |

No user-specific CUDA, C or RTL incident catalog is invented where evidence is
missing. Add new notes through $jagent-env-promote after inspecting a real incident.

A note must state the failure mechanism, applicable conditions, what to check,
what does NOT prove the diagnosis, and the evidence limitation. Keep original
runs, code identifiers and quantitative outcomes in the originating project.
Portable notes are not an alternative place to store project experiment history.
