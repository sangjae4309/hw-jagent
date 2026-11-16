# Code-style routing

Always read common.md. Read cpp.md for C/C++, plus c.md for C, hls.md for HLS,
cuda.md for CUDA, python.md for Python, or rtl.md for RTL. Also read
[code-pitfall/INDEX.md](../code-pitfall/INDEX.md); style does not replace failure
checks. Do not load every language on every task.

Approved project-only exceptions belong in .agent/memory/project/STYLE_OVERRIDES.md.
Portable source rules live in the external environment's general/code-style/.
Installed rules are versioned snapshots. Use env-curator / $jagent-env-promote for a
reviewed source change; use the source install.sh --update to distribute it.
There are no bundled original-project backups or histories.
