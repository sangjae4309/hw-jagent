---
name: domain-modeling
description: Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing the project glossary, or recording or editing an ADR.
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline: challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `.agent/memory/project/GLOSSARY.md` for vocabulary is not this skill: that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

## Repository routing

Read root AGENTS.md and .agent/memory/INDEX.md. The canonical glossary is
.agent/memory/project/GLOSSARY.md; ADRs live in .agent/memory/project/decisions/.
Capture agreed terms and qualifying decisions, not unanswered questions as facts.
During a jagent-transfer interview before this environment is active, keep drafts
in the migration plan; do not switch canonical paths or overwrite old docs until
the user approves migration. Then relocate retained history to canonical memory
and remove old controls without backups; follow the approved transfer plan.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `.agent/memory/project/GLOSSARY.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account': do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is right?"

### Update .agent/memory/project/GLOSSARY.md inline

When a term is resolved, update `.agent/memory/project/GLOSSARY.md` right there. Don't batch these up: capture them as they happen. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md).

`.agent/memory/project/GLOSSARY.md` should be totally devoid of implementation details. Do not treat `.agent/memory/project/GLOSSARY.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse**: the cost of changing your mind later is meaningful
2. **Surprising without context**: a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off**: there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).
