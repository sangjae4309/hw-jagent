# Shared engineering preferences

Keep changes small, explicit and source-grounded. Read existing code and relevant
style first. Preserve numerical behavior, established interfaces and others' work.
Do not introduce generic frameworks or speculative fallbacks for a local task.
Separate subprocess running from data loading, tables and plotting.
Keep design, verification, and measured evidence distinct. Missing results are
unknown, not success or zero. Use approved runners and exact artifact scopes.
Do not run FPGA/C++ verification merely because a role or guideline mentions it.
Do not add synthesized debug/status circuitry without explicit approval.
