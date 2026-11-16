# Memory ownership and lifecycle

Portable preferences and failure lessons are installed under .agent/rules/code-style/
and .agent/rules/code-pitfall/. The external environment general/ directory is the
source of those snapshots. New projects start with no old project knowledge.

| Material | Canonical location/owner |
| --- | --- |
| Project purpose and constraints | project/PROJECT.md, CONSTRAINTS.md |
| Whole-design architecture | project/ARCHITECTURE.md |
| Current status / project exceptions | project/STATUS.md, STYLE_OVERRIDES.md |
| Terms and durable choices | project/GLOSSARY.md, project/decisions/ |
| Block design and accepted feedback | blocks/<id>/MEMORY.md, block owner |
| Specialist's project methods | agents/<role>/MEMORY.md |
| Run metrics and evidence | experiments/<id>/record.json, immutable |
| Analysis and owner responses | findings/, blocks/<id>/inbox/ and receipts/ |
| Transferred historical knowledge | history/; original paths in migration-map.json |
| Generalization proposals | ignored .agent/drafts/; receipt under agents/env-curator/ |

Every material entry states scope, evidence locator, status (observed, inferred,
proposed, historical, disputed) and source/review identity. Unknown is not zero.
Keep failed alternatives and their conditions. Do not duplicate metrics in many
summaries. Do not treat an old source hash as current verification.

At task start, read the relevant memory/inbox and both style/pitfall indexes.
Compare owned source to .agent/blocks.json fingerprints. At task end update the
current summary, record material evidence and acknowledge delivered feedback.
Use block refresh only AFTER reviewing changed source. Do not dump chat transcripts.

Analysts return evidence -> integrator publishes finding -> parent dispatches
block owners -> owners inspect/accept/reject/defer -> accepted links appear in
block memory. File delivery alone does not run agents. Report missing responses.

Use agentctl for registry, immutable ledger, inbox and receipt operations.
Hand-edited Markdown still needs one writer. File operations use locking and
atomic per-file replacement, but there are no disk snapshots or rollback commands.
A process/machine crash can interrupt a multi-file change.

On transfer, remove old agent controls rather than keeping a parallel rule system.
Move useful old history into canonical history/ or integrate it into new memory
and remove the old source files. Retain unrelated project guides only by explicit
plan classification. Historical instruction text is evidence, not current authority.
Imported prose paths may need migration-map.json; check links before relying on them.
Do not turn imported numbers into current verified run records without provenance.
