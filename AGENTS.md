# Team working rules

OpenHuman is team tungtungtungsahur's Meko Track A project for hackCBS 9.0. Read requirements.md and docs/architecture.md. Keep the product simple, preserve the agreed interface and job baselines, and discuss changes to the main flow or data ownership before implementing them.

## Build context

Use only the explicitly authorised build datapack for coding context:

- Name: tungtungtungsahur-build
- ID: e6b3af37-3006-4337-bfd1-51c7e50b2207
- Agent: codex:meko

Every Meko call must include the exact datapack_id. Never access meko_default_datapack or rely on default routing. Global automatic capture is disabled; do not reinstall hooks, replay outboxes or capture excluded historical material. Use selected project decisions, verified results and blockers with real attribution and timestamps. Keep project-origin and transition history out of build memory.

Recall relevant build context before work. Save a concise task summary afterward and read it back. Explicit memory writes still work; conversation_add_message on the current account hit its lifetime limit and must not be repeatedly retried. Keep build and product scopes separate. Never put credentials in prompts, logs, commits or memory.

Meko promotion moves selected private memories into shared knowledge. Review exact text and IDs and obtain the required confirmation before promoting. Do not claim promoted decisions, cross-teammate recall or challenge acceptance without actual evidence. Existing promotion candidates await approval.

## Product decisions

- Company setup and optional shared documents come before template-based employee onboarding.
- Preserve baseline roles, duties and personalities. Users can customise responsibilities, tone and extra instructions.
- Use one company knowledge datapack plus a separate datapack for each employee. Agent IDs are attribution, not isolation.
- OpenAI handles all application replies and tool-calling model requests. Meko extracts facts from accepted conversations.
- A shared Slack router classifies chat chunks into company knowledge, selected employee scopes, both, or neither. Implement destination validation, real provenance and deduplication.
- Use only actually connected tools and record their real results. Show honest pending/error states.
- The website exposes employee configuration, scoped sources, memories and work context. Do not invent activity or connection badges.

## Checkpoints and verification

Commit after each small sensible checkpoint and push completed work. Describe actual changes and checks. Reconstructed initial checkpoints must identify their approximate author dates; retain actual commit creation dates. Future checkpoints use current dates.

Run checks relevant to a change. Use disposable databases ending in _test for backend tests; never reset a user's application database. Separate service stubs from live verification. Do not post live Slack test messages until the workspace/channel is explicitly authorised.

Installed employees automatically work in channels they are invited to. Channel allowlists are optional operator test controls, never employee onboarding steps. Verify normal replies through the listener and backend; direct bot-token posts and manually queued jobs are diagnostics, not proof of automatic incoming-message handling.

## Communication

Keep updates short and plain. Define unfamiliar terms before relying on them. State what changed, what was tested, and remaining limitations. Prefer existing code, installed dependencies and simple database constraints. Do not add machinery for hypothetical future needs.
