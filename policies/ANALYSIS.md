# RTL and hw_emu analysis

## RTL analyst (static evidence)
Identify exact build, source/config digest and tool. Inspect hierarchy and actual
instantiations, scheduled operator sharing, FSM/caller feedback, loop-carried
recurrences, memory ports/banking, address logic, FIFO interfaces and valid/ready
conditions. Link source symbols to generated RTL and schedule/report locations.
UNROLL/DATAFLOW directives alone prove neither replication nor overlap. Separate
potential stalls from observed stalls. Do not edit generated RTL or start builds.

## hw_emu analyst (dynamic evidence)
Read only the exact assigned run. Inspect format/headers/units before parsing.
Define start/end boundary and clock domain; identify resets and warm-up. Correlate
profile/timeline entries or exported waveform signals with this build's hierarchy.
Separate compute, memory wait, upstream starvation, downstream backpressure,
FIFO-full/empty, caller serialization and feedback. Unknown causality stays unknown.
Union overlapping intervals: inclusive parent + child or parallel lanes must not
be summed as elapsed time. State unattributed time and observation coverage.
Distinguish kernel simulation time from host time and emulator wall time.

A .wdb is not assumed to be a directly readable text file. Detect a supported
installed vendor reader/exporter; otherwise request CSV/VCD or an existing signal
export from that exact build. No invented waveform observations, no unconditional
parser support claim. VCD also needs timescale/signal/hierarchy mapping.
The optional intervals.py helper accepts ONLY its documented normalized CSV,
not arbitrary vendor timeline formats. Converting headers/units is explicit.

## Integration
Join static and dynamic evidence only when build/config/source identities match.
Retain contradictions, missing signals and alternatives. Rank proposed changes by
measured non-overlapping time budget, correctness risk and resource tradeoff.
For a serial fraction f, 1/(1-f) is only the ideal infinite-acceleration bound;
overlap and secondary bottlenecks can invalidate a naive application. Never promise
speedup from source changes alone. Do not add diagnostic hardware to get evidence.
Publish findings with affected blocks, experiment IDs, confidence and next-design
checks. Ask each owner to acknowledge, then verify a proposed change in a separately
authorized experiment. Preserve rejected optimizations to avoid repeating them.
