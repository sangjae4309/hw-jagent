# Project memory

- project/PROJECT.md: purpose, platform, scope; do not guess values.
- project/CONSTRAINTS.md and STYLE_OVERRIDES.md: approved project-only constraints.
- project/ARCHITECTURE.md and STATUS.md: architecture and concise current state.
- project/GLOSSARY.md and project/decisions/: terms and durable choices.
- blocks/<id>/MEMORY.md: owner-reviewed design and accepted findings.
- agents/<role>/MEMORY.md: specialist methods in this project.
- experiments/<id>/record.json: immutable quantitative evidence and hashes.
- findings/<id>.json: immutable analysis; inboxes/receipts record owner responses.
- history/ and migration-map.json: canonical transferred history, when present.

Read BOTH .agent/rules/code-style/INDEX.md and .agent/rules/code-pitfall/INDEX.md
before design work. HLS address changes require hls-signed-index.md.

Use agentctl memory search QUERY for recall and doctor for integrity checks.
Use $jagent-block-add to register one owner without a full scan. Use $jagent-env-promote
for selected generalized lessons, not to export this project's entire memory.
