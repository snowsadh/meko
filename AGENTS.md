# Team working rules

This repository is team **tungtungtungsahur**'s entry for the **Meko challenge, hackCBS 9.0, Track A**. Read `requirements.md` for the challenge requirements and acceptance criteria. Do not treat an unchosen product idea or an untested behavior as an established decision or result.

## Shared Meko build memory

A **datapack** is Meko's container for saved context. All teammates' coding agents use this shared build datapack:

- Name: `tungtungtungsahur-build`
- Identifier (`datapack_id`): `e6b3af37-3006-4337-bfd1-51c7e50b2207`
- Model Context Protocol (MCP) endpoint: `https://mcp.mekodata.ai/mcp`
- Authentication: each teammate uses their own key, supplied through `MEKO_API_KEY` in their local environment.

Pass this `datapack_id` explicitly on build-memory calls. Do not silently use an account's default datapack. Never commit a key or include it in a prompt, memory, log, or task summary.

Each teammate must accept the invitation as a **Maintainer**, the role that allows promoting memories to shared knowledge. An invitation alone does not verify that the teammate's coding agent is connected.

Use the agent and conversation identifiers supplied by the current client session when available. Without an existing session, follow Meko's documented setup: use a stable agent identity such as `codex:meko` for Codex in this repository, create a conversation in the build datapack, and reuse the returned conversation identifier. Do not invent conversation identifiers or copy another teammate's session identifier. An agent identifier attributes activity; it is not a privacy boundary.

When available, follow the Meko tools skill at `~/.agents/skills/meko-mcp-tools/SKILL.md` for tool contracts. Use the schemas exposed by the connected server.

## Before every task

1. Recall relevant build context with `context_search` in the shared build datapack. This searches personal memory, shared knowledge, and past conversations.
2. Read the relevant repository files and compare them with recalled decisions. Use `memory_search` for personal memory or `knowledgebase_search` for shared decisions when a single source is needed.
3. Follow applicable team decisions. Surface conflicts or superseded decisions rather than silently choosing between them.
4. If Meko is unavailable, report that recall could not be completed. Do not describe a failed call as an empty memory store or claim that shared context was checked.

## While working

- Record actual decisions as they arise: interfaces, data shapes, conventions, datapack boundaries, task ownership, workarounds, and pitfalls others need to know.
- Keep each decision focused and include the teammate who made it, the decision, its reason, and affected work. Attribute the decision to the person, not just the model or coding tool. Establish the teammate's name if it is unknown; never invent attribution.
- Record friction with Meko and the workaround actually used. These records provide evidence for the required Meko feature proposal.
- Keep source code and canonical specifications in the repository. Use Meko for durable context and concise summaries; do not copy entire files or transcripts into individual memories.
- Distinguish proposed work, completed changes, observed results, and unverified assumptions. Never fabricate decisions, test results, timestamps, or contributions.

## At the end of every task

1. Save a short summary in the build datapack: what changed, why, relevant files or commit, verification performed, and any remaining issue. Use an explicit memory write when automatic capture does not establish that the summary was stored.
2. Read the saved summary back in the same datapack before reporting it as persisted. A successful-looking write response alone is insufficient.
3. **Promote every decision the other teammates must follow.** Promotion publishes selected memory into the datapack's shared knowledge; saving a private memory alone does not satisfy this step.
4. Follow Meko's promotion review contract: show the exact memory text and identifiers, explain that promotion makes them team-visible and removes the private records, and obtain confirmation for those exact entries before calling `memory_promote`. Use existing confirmation when it already covers those entries. Never report a pending or failed promotion as complete.
5. Verify promoted decisions through shared-knowledge retrieval, including from another teammate's agent when checking cross-teammate access.

## Keep build and product data separate

- Coding agents use only the build datapack for development context. They must not read or write the product's datapacks.
- The running product uses separate datapacks and must never read the build datapack.
- Do not put keys or personal data in build memory. Include the teammate attribution required by the challenge without adding unrelated personal information.
- Treat the build datapack as a team workspace that judges will also view. Do not assume unpromoted content is hidden from every portal or search surface.

## Evidence required for judging

- Accumulate at least **10 real promoted decisions in total**, contributed through at least **2 different teammates' coding agents**. Every decision names its teammate.
- Summaries, connection tests, and fabricated filler do not substitute for those decisions. Collect them throughout the event.
- Invite judges to the build datapack as **Viewers** before judging.
- Be ready for **Check T**: one teammate's coding agent must answer a question about another teammate's decision using Meko, live.

## Communication

- Write for a human reading from beginning to end. Define unfamiliar terms and acronyms before their first use, then explain in dependency order.
- When teaching or clarifying, assume no prior knowledge. Start with the concrete task and a simple example; explain what each part receives, does, and produces, and why it exists.
- Explain where models, configurations, and decisions came from; what was reused; what changed; and what was not reused. Distinguish architecture, trained weights, training feedback, and experimental conditions.
- Use readable sentences with enough detail to connect necessary steps. Tables may summarize an explanation, not replace it.
- Ground claims about experiments in actual code and the recorded protocol. Separate implementation, illustrative examples, design intent, and limitations. Do not invent history or imply an unmeasured result.
