# Vitis HLS code style

Read cpp.md and ../code-pitfall/INDEX.md. Before design changes read the relevant
HLS pitfall notes, especially addressing, recurrences and physical resource sharing.

## Source organization and pragmas

Use ordinary functions and explicit loops. Do not introduce custom template or
recursive hardware dispatch; existing library types such as ap_uint and hls::stream
are permitted. Keep directives local to the evaluated design variant.

Use uppercase HLS pragmas. Put ARRAY_PARTITION immediately after the declaration.
Put function/argument directives at column zero just after the opening brace.
Put loop directives inside the loop, aligned with the for statement. Label
important loops and give each added/edited loop one short comment describing
what its index counts. Use the C++ profile's 120-column formatting rules.

```cpp
void process_values(value_t values[CAPACITY])
{
#pragma HLS INLINE off
    // index: input values #
    PROCESS_VALUES: for(count_t index = 0; index < CAPACITY; index++) {
#pragma HLS PIPELINE II=1
        values[index] = transform_value(values[index]);
    }
}
```

For a known supported capacity, prefer a constant loop bound with a runtime exit
before accesses or stream I/O. Preserve inclusive terminal actions and matching
producer/consumer token counts. Do not invent a capacity from observed samples.
Counters must represent the terminal bound, not just valid element addresses.
A constant bound plus break still has variable execution length; inspect synthesis.
LOOP_TRIPCOUNT is reporting, not an optimization. Use explicit fixed stages when
variable-stride reductions prevent the intended unroll.

## Sharing and bit representation

When sharing a function instance, prefer one ordinary source call site inside a
sequential loop. Do not UNROLL that loop when reuse is intended. ALLOCATION alone
is not proof of sharing; inspect the generated hierarchy and schedule.

For a Vitis design already using FP32 bit-packing unions, preserve that pattern
unless a verified change is authorized. Assigning float to an integer field is
numeric conversion, not bit copying. This is a Vitis-specific preference, not a
claim that union type-punning is portable to every host or CUDA compiler.
Do not replace it with memcpy solely for appearance without checking synthesis.

## Execution

Use the project's inspected runner only for the explicitly authorized stage.
A style rule does not authorize compilation, synthesis or emulation. Read
.agent/system/policies/EXPERIMENTS.md for evidence requirements.
