# Python utility script style

Canonical reference for repository utility scripts, Python roles and skills.
Root AGENTS.md and explicit user instructions govern scope and exceptions.

## Scope and structure

- Prefer short, direct scripts and helpers focused on the actual workflow.
- Avoid generic frameworks, broad fallback parsing and speculative validators.
- Preserve existing behavior; refactor only what the assigned change requires.
- Keep subprocess execution/logging separate from table/figure generation.
- Use each workflow's local README for paths, commands and generated artifacts.

## Cases and CLI

- When an existing hardware workflow uses user-edited CFG case catalogs, preserve
  that catalog and the runner's selection interface. Do not introduce cases.py
  as their case-control entrypoint. Existing optional catalog arguments are valid.
- Other utility workflows may use top-level constants and cases.py with CASES.
  Preserve their existing documented interface unless migration is requested.
- CASES rows should be compact positional lists with a nearby field-order comment;
  convert to typed records in selected_cases() when useful. Shared values belong
  in named constants, not repeated rows.
- Avoid argparse/required CLI arguments for routine new scripts when editable
  cases suffice. Optional arguments are appropriate when the workflow needs them.
  Do not remove an existing runner interface merely to enforce this preference.

## Execution and outputs

- Runner scripts capture stdout, stderr, return code and elapsed time, and save
  logs to explicit paths. Report failures clearly; preserve useful failure evidence.
- Data/table/figure scripts use identified input paths and explicit output paths.
  Handle malformed/missing data according to the real workflow; never invent it.
- Follow the protected-artifact access restriction before searching or reading those artifacts.
- Prefer authorized narrow checks or existing dry-runs for runner changes. An
  import can have side effects: inspect before importing job-launching modules.
  Do not launch expensive jobs or C/C++/FPGA checks without required authorization.

## This toolkit

The agent infrastructure CLI intentionally uses command-line arguments: installation targets, migration approvals and immutable ledger operations require explicit invocations. This is a tooling interface, not a replacement for hardware CFG catalogs.
