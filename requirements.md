---
title: "Meko Challenge - hackCBS 9.0 - Track A Requirements"
track: A
track_name: Open project
source_reviewed_on: 2026-10-31
event_dates: "2026-10-31 to 2026-11-01"
document_status: OpenHuman design approved; implementation in progress
verification_status: Checks and limits recorded in docs/architecture.md; challenge acceptance pending
---

# Meko Track A requirements

## Current build direction

OpenHuman is the selected company-coworker product. The previous capability selection is superseded: choose Meko uses that help this product, rather than preserving a fixed checklist.

The confirmed product flow is company setup with optional shared documents, followed by onboarding employees from job templates, customising duties/instructions, adding employee documents, and connecting them to Slack. The website manages employees, documents, memories, and activity. One shared router selects chat destinations: company knowledge, selected employees, both, or neither. Meko extracts private facts from accepted employee conversations. The approved integration plan is in [docs/architecture.md](docs/architecture.md); the supporting documentation review is in [docs/meko-notes.md](docs/meko-notes.md). The user approved separate employee datapacks and implementation. After the owner connects an employee to Slack, it automatically works in channels it is invited to. Per-channel listener activation is not part of onboarding. Live test posts still need an authorised destination.

Natural uses are A2.1 (knowledge scopes), A2.2 (extracted facts), A2.3 (recall), A2.5 (sharing), and A2.6 (documents). Native A2.4 promotion does not move facts between datapacks; our cross-pack publication must not be called native promotion. These candidate categories still need a working product demonstration. The approved layout is one shared company datapack plus one private datapack per employee. YugabyteDB is the application database, separate from Meko's managed storage. OpenAI handles all application agent and tool-calling model requests; Meko manages its internal extraction.

Keep the product small and useful. Discuss decisions that change its purpose, user experience, or main architecture with the user before committing to them. Handle routine implementation details without unnecessary approval steps.

## Start here: what we need to remember

1. **First, connect Meko to the coding agent used in this chat.** Create `<team>-build`, our shared **datapack** (Meko's container for saved context), and verify that this agent can save and retrieve information there. Treat the connection as pending until that works. Each teammate uses their own key; keep keys out of chat and saved memory.
2. **Connect the whole team.** Invite teammates as Maintainers. Add the working protocol to `AGENTS.md`: read relevant build memory before each task, save a short summary afterward, and **promote** decisions, meaning make them shared knowledge the other teammates' agents can retrieve.
3. **Collect evidence while building.** We need **10 promoted decisions total from at least 2 teammates' coding agents**, each naming its teammate. Judges get Viewer access and will test whether one agent can recall another teammate's decision live.
4. **Keep development memory separate from app memory.** Use only the build datapack in this chat; give the running app separate product datapacks. Never mix them.
5. **Pick one user and one problem where remembering helps.** The same flow must give a clearly better result with Meko enabled than disabled. Use **at least 3 of the 6 qualifying capabilities** listed under A2 below.
6. **Make memory visible and controllable.** Show what the app actually recalled and stored; let the user correct or forget it. Use only personal data the story needs.
7. **Keep the submission small and complete.** Repository setup in **5 commands or fewer**, product demo in **5 minutes or less**, and **one new Meko feature proposal** based on friction we actually encounter. Record that friction as we go.
8. **For the public-build points:** post a short LinkedIn demo explaining Meko's role and mentioning **Meko, YugabyteDB, and hackCBS 9.0**. Build the project during the event; follow the event rules.

The detailed requirements, qualifying capabilities, scoring, and open questions follow.

---

Build an app of our own choosing in which remembered information changes what a user gets. Demonstrate the same task with Meko enabled and disabled, use at least three of the six qualifying Meko capabilities, and propose one new Meko feature based on friction encountered while building.

There are two separate uses of Meko to satisfy: the product uses it while running, and the team's coding agents (tools that help write and change the app) use it while building. Completing only one does not satisfy the challenge.

This file records the challenge requirements and current direction above. The user selected **Track A** and **OpenHuman** and approved the company/employee/Slack flow, separate datapacks and shared chat router. A concrete demo will illustrate this product flow.

## 1. How to read and maintain this file

- **MUST** means an explicit Track A or shared challenge requirement.
- **SCORED** means a judging opportunity; the brief does not describe it as a participation gate.
- **RECOMMENDED** means a practical verification or implementation suggestion added in this document, not an extra organizer rule.
- **OPEN** means the brief does not settle the detail. Do not silently turn it into a requirement or a confirmed fact.

Requirement identifiers are stable. `A1`-`A5` come from the brief; the other identifiers are local labels for shared rules, deliverables, and proposal contents. `BUILD1`-`BUILD6` refer to development rules, not the brief's Track B product requirements. Each requirement states what is required and how to establish completion. Suggested evidence is not an extra submission artifact unless explicitly identified as a deliverable.

For implementation tracking, reference these identifiers in tasks and record `status`, `owner`, and `evidence` against each. Suggested statuses: `not_started`, `in_progress`, `blocked`, `verified`. Mark a requirement `verified` only after its acceptance criteria have been demonstrated. All project requirements currently remain unverified.

### Sources and authority

| Source | Use in this document |
| --- | --- |
| [S1: Official challenge brief, “meko hackathon 31-01.pdf”](https://drive.google.com/file/d/1mk8SUU118v_hagb0OZxix8616UccEbwX/view) | Authority for requirements and scoring. Five pages; Drive modified time was 2026-10-31 04:20:22+00:00 when reviewed. |
| [S2: Meko website](https://mekodata.ai/) | Product overview and positioning; does not add competition requirements. |
| [S3: Yugabyte introduction to Meko, 7 May 2026](https://www.yugabyte.com/blog/meko-data-infrastructure-for-agents-that-work-and-learn-together/) | Background on persistent memory, shared knowledge, conversations, and traces; does not add competition requirements. |
| [S4: Meko documentation](https://docs.mekodata.ai/) | Current technical behavior and integration reference, linked by the brief. Specific pages are cited below. |

Use S1 for what judges require and S4 for how the current service works. The supplied website and blog were read as background. Their descriptions of the broader platform do not imply that every advertised capability must be built into our app. Separate hackCBS event rules still apply; they were not independently supplied or reviewed here.

## 2. The basic concepts

For example, a tutor could remember that a learner confuses two concepts and tailor a later explanation accordingly. Without that remembered fact, the same request receives a generic explanation. This is an illustration, not our chosen idea.

- **Context:** information from earlier interactions or reference material that helps with the current task.
- **Agent:** software that uses an artificial intelligence model to perform a task and, where needed, call tools. A **coding agent** helps the team develop the app; a **product agent** runs inside the app for its users.
- **Datapack:** Meko's container for scoped conversations, memory, and knowledge. The build datapack holds development decisions; product datapacks hold app context.
- **Memory:** a durable fact, preference, decision, or outcome extracted from an interaction, rather than merely a raw chat transcript.
- **Recall:** retrieve relevant context before the agent forms an answer or takes an action.
- **Promotion:** explicitly move selected memory into knowledge available to other members of the datapack. Saving a memory and promoting it are different operations.
- **Model Context Protocol (MCP):** the protocol through which an agent can discover and call Meko tools.
- **Application programming interface (API):** a software interface for making requests. Each teammate uses their own Meko API key to authenticate.
- **User interface (UI):** the screens and controls the product's user interacts with.
- **Large language model (LLM):** the model an agent uses to interpret requests and generate responses or tool calls.

The task-level flow is: receive a user request, recall relevant Meko context, use it in the agent's answer or action, and save useful new information for later. If selected for A2, promotion and sharing make an appropriate lesson reusable by another user or agent. [S1, pp. 1-2; S4: [Datapacks](https://docs.mekodata.ai/architecture/core-concepts/datapacks/), [Memory](https://docs.mekodata.ai/architecture/core-concepts/memory/), [Learnings](https://docs.mekodata.ai/architecture/core-concepts/learnings/)]

## 3. Shared event and build requirements

These apply to Track A as well as Track B. Source: [S1](https://drive.google.com/file/d/1mk8SUU118v_hagb0OZxix8616UccEbwX/view), pp. 1-2.

| ID | Level | Requirement | Completion evidence |
| --- | --- | --- | --- |
| E1 | MUST | Participate as a team of two to four students at the in-person event at Shaheed Sukhdev College of Business Studies, New Delhi, 31 October-1 November 2026. | Team roster and event participation. |
| E2 | MUST | Build the project during the event; no pre-existing projects. Meko account and coding-agent setup may happen beforehand. Add the repository's agent protocol and begin recording project decisions only once hacking starts. | Repository history and build records consistent with the event timeline. |
| E3 | MUST | Follow the applicable hackCBS rules in addition to this challenge brief. | Check the separate event rules; this file does not replace them. |
| BUILD1 | MUST | Use coding agents connected to Meko while building. Each teammate connects their coding agent using their own key. Supported examples include Codex, Claude Code, Cursor, and Copilot or similar clients. | Each teammate can demonstrate an authenticated connection from their coding agent. |
| BUILD2 | MUST | Create one shared build datapack named `<team>-build`. The creating teammate invites the other teammates as **Maintainers**, so they can promote decisions. | Shared datapack exists and teammates' roles are correct. |
| BUILD3 | MUST | Put the team protocol in a repository instruction file such as `AGENTS.md`, `CLAUDE.md`, or `.cursorrules`: recall the build datapack before every task; save a short summary after every task; promote decisions the rest of the team must follow. | Instruction file is committed and the coding agents actually follow it. |
| BUILD4 | MUST | Keep build and product datapacks separate. Coding agents never access product datapacks; the product never reads the build datapack. | Distinct configured datapack identifiers and observed calls to the intended datapacks. |
| BUILD5 | MUST | Keep API keys and personal data out of the build datapack. The brief separately requires naming the teammate responsible for each Check T decision; include that attribution without adding unrelated personal data. | Inspect build entries for secrets and unnecessary personal information. |
| BUILD6 | MUST | Invite judges to the build datapack as **Viewers**. | Judges have the required access before judging. Their identities/invite details need to come from organizers. |
| T1 | MUST | The build datapack contains **at least ten promoted decisions in total**, contributed through **at least two different teammates' coding agents**. Every decision names the teammate who made it. | Inspect promoted records, teammate attribution, and contributions from at least two teammates. Ten private memories do not meet this requirement. |
| T2 | MUST | Pass **Check T**, the live team-context check: ask one teammate's coding agent about a decision made by another teammate; it answers using Meko. | A live cross-teammate recall, grounded in the promoted build decision. |

**RECOMMENDED build records:** capture decisions about interfaces, data shapes, datapack names, conventions, workarounds, and pitfalls when they actually arise. Include the decision, its reason, the teammate attribution, and affected work. Do not fabricate decisions or backdate activity to meet T1.

**Technical note:** private-memory search is scoped to the authenticated user, not isolated by the supplied agent identifier. Other members may see memories in portal/API listings, and conversation search can have broader visibility. Treat the build datapack as a shared team workspace and explicitly promote decisions needed for Check T. Do not rely on an agent name as a privacy boundary. [S4: [Datapacks, isolation model](https://docs.mekodata.ai/architecture/core-concepts/datapacks/), [MCP reference, context and memory search](https://docs.mekodata.ai/reference/mcp-server/)]

## 4. Track A product requirements

All five are **MUST** requirements. Source: [S1, Track A table, p. 2](https://drive.google.com/file/d/1mk8SUU118v_hagb0OZxix8616UccEbwX/view).

### A1 - Context changes the outcome

**Required:** demonstrate the same user flow with Meko enabled and disabled, producing clearly different results. Meko must materially affect what the user receives; the brief rejects a product that works just as well with Meko switched off.

**Acceptance:** show both runs, identify the useful context returned by Meko in the enabled run, and explain the resulting difference in the user's answer, action, or outcome.

**RECOMMENDED verification:** keep the user request, model, and other conditions equivalent so the difference can be attributed to retrieved context. The disabled run should still attempt the task. Avoid a comparison that only shows an intentional crash, a manually worsened answer, or a changed model. State any setup differences and distinguish an observed result from an expected one.

### A2 - At least three meaningful Meko uses

**Required:** use **at least three distinct categories** from the following six in the product, with an explainable reason for each. Repeating one category does not create additional categories. Build-time Meko usage satisfies the BUILD/T requirements, not this product requirement.

| Local ID | Qualifying category from S1 | What meaningful use should demonstrate | Selection |
| --- | --- | --- | --- |
| A2.1 | Datapacks as scopes | Context is organized into a useful boundary, with an explanation of what belongs there and who should access it. | Proposed: company and employee knowledge boundaries |
| A2.2 | Extracted memories | Information from an interaction becomes durable facts usable later, rather than only an appended chat log. | Proposed: automatic facts from eligible employee conversations |
| A2.3 | Recall before reasoning | Relevant stored context is retrieved before forming the answer or action and influences it. | Proposed: recall before coworker work |
| A2.4 | Promotion to shared knowledge | A selected lesson becomes shared knowledge for a reason the team can explain. | Optional; layout-dependent; cross-pack copying is not native promotion |
| A2.5 | Sharing across users or agents | Another user or agent benefits from context shared through Meko. | Proposed: another coworker uses an earlier lesson |
| A2.6 | Documents | Relevant document content is used through Meko as part of the product's task. | Proposed: company files inform the task |

The examples in this table are verification guidance, not additional organizer-prescribed workflows. A single flow may demonstrate several categories, but explain each separately.

**Acceptance:** identify the selected categories, show their real use in the running product, and explain the user benefit of each. All six are optional individually; at least three are mandatory collectively. Product datapack count and agent count are design decisions for Track A.

**RECOMMENDED evidence:** maintain a small mapping of selected A2 IDs to the relevant app flow, actual Meko operation, observed result, and rationale. Record the live tool schema used during implementation rather than inventing names or parameters.

### A3 - One user, one problem, one demo story

**Required:** define one **persona**, meaning the representative person using the product; one problem they face; and one demonstration story where context changes the outcome.

**Acceptance:** the team can explain who the user is, what they are trying to do, what information matters, how it is remembered, and why recalling it improves the result. The demo follows that story coherently.

Any hackCBS theme is allowed, including artificial intelligence, education technology, health technology, financial technology, environmental technology, the Internet of Things, cloud, or open innovation. The brief's tutors, lab notebooks, support desks, game masters, issue-triage bots, and coaches are inspiration, not a required menu.

### A4 - Visible and controllable context

**Required:** the UI shows what was recalled and what was stored, and lets the user correct or forget context.

**Acceptance:** a user can inspect recalled information and newly stored information and use the correction/forget controls. A storage or deletion claim must reflect what actually happened.

**RECOMMENDED verification:** correct a remembered fact, then repeat a relevant task and confirm the corrected version is used. Forget a fact, then confirm it is no longer used from the affected store. If the fact has been promoted or copied into another context source, account for that copy and explain the scope of the operation. Hiding a card in the UI alone does not establish that Meko context was changed.

The brief does not prescribe a screen layout, a deletion implementation, or an exact policy for promoted copies. Those need to be designed and verified against the available Meko operations.

### A5 - Honest context and minimal personal data

**Required:** use no personal data that the story does not need. Never display information as retrieved Meko context unless Meko actually returned it.

**Acceptance:** displayed context can be traced to actual Meko responses; model-generated conclusions are distinguishable from those retrieved facts; the data used is limited to what the story requires.

**RECOMMENDED verification:** use synthetic identities where possible. Check empty results and failed Meko calls so the UI never substitutes invented memories. Show a successful write only when storage has succeeded; distinguish a pending extraction from a confirmed memory.

## 5. Submission and demo deliverables

Source: [S1, p. 1 submission table; p. 3 feature proposal; p. 4 scoring](https://drive.google.com/file/d/1mk8SUU118v_hagb0OZxix8616UccEbwX/view).

| ID | Level | Deliverable | Acceptance |
| --- | --- | --- | --- |
| D1 | MUST | Project repository with a README. | The README gets the app set up in **five commands or fewer**. |
| D2 | MUST | Product demonstration of **at most five minutes**. | Shows the same flow with Meko on and off, with a clear, working story and evidence for A1-A5. |
| D3 | MUST | One proposed new feature for Meko. | Covers F1-F6 below and is grounded in actual build friction, with build-datapack evidence. |
| P1 | SCORED | LinkedIn project post. | Includes a short demo, explains what Meko does in the project, and mentions **Meko, YugabyteDB, and hackCBS 9.0**. Worth five base points. |
| P2 | SCORED | Build-in-public bonus. | Posts with the most likes by judging time receive bonus points above the base total. The brief does not specify the bonus formula. |

**RECOMMENDED README contents:** required tools/accounts, environment-variable names without secret values, the setup commands, how to run the demo, Meko on/off instructions, the selected A2 categories, and a link to the feature proposal. Validate the instructions from a clean checkout. State any manual account or credential prerequisites transparently; the brief does not define how judges count those steps.

**RECOMMENDED demo order:** introduce the persona and task; run the task without Meko; run the same task with Meko and show the recalled context; demonstrate storage and user correction/forgetting; explain the selected A2 uses. Rehearse to fit the five-minute maximum. Confirm with organizers whether Check T and the feature pitch have separate judging time.

Track A requires genuine Meko-backed behavior. The explicit rule that every demonstrated step calls Meko live appears in the Track B section, not the Track A table. Live product evidence is recommended for a convincing Track A demonstration; **Check T is explicitly live for both tracks**.

This requirements file is a planning artifact. It does not itself replace the repository README, product demo, or Meko feature proposal.

## 6. Meko feature proposal contents

The proposal is about a new capability **in Meko itself**, alongside the app. A bug report alone does not qualify. Source: [S1, “The Meko feature proposal,” p. 3](https://drive.google.com/file/d/1mk8SUU118v_hagb0OZxix8616UccEbwX/view).

Any format is allowed. The brief suggests a PDF, slide deck, or document of about **one to three pages**, or a video of **up to three minutes**. The page count is approximate guidance; the video duration is stated as an upper bound.

| ID | Level | Required content | Acceptance |
| --- | --- | --- | --- |
| F1 | MUST | Real friction and workaround. | Explain what could not be done, or was awkward, and what the team actually did instead. Ground this in build-datapack records. |
| F2 | MUST | The proposed feature in Meko's terms. | Explain how it relates to datapacks, memories, promotion, or sharing as applicable. |
| F3 | MUST | Proposed interface. | Include a new MCP tool or parameter and an example request and response. Clearly label the interface as proposed, not currently available. |
| F4 | MUST | A before-and-after scenario. | Show the current workaround and how the proposed feature would change it. |
| F5 | MUST | Novelty. | Explain what existing context layers do not provide today. Support the comparison; do not assert novelty without checking. |
| F6 | MUST | Risks and limits. | Address privacy, cost, and abuse, with practical ways to limit each. |

Judges assess originality, grounding in actual friction, feasibility, and impact. Implementing the new Meko feature is not listed as a deliverable. Record friction during the build so the final proposal has real evidence; do not invent a building history afterward.

## 7. Track A scoring

Source: [S1, “How we score,” p. 4](https://drive.google.com/file/d/1mk8SUU118v_hagb0OZxix8616UccEbwX/view).

| Category | Points | What judges assess | Requirements to demonstrate |
| --- | ---: | --- | --- |
| The idea | 20 | Originality, a real problem and user, and an outcome that changes with context. | A3, supported by A1 |
| Meko's role | 30 | Meko materially changes the flow; at least three justified uses; visible context. | A1, A2, A4 |
| Build and execution | 25 | Working product, clear demo within five minutes, setup within five commands, honesty and privacy. | A5, D1, D2 |
| Built with Meko | 10 | Coding agents connected to a shared build datapack and a passing Check T. | BUILD1-BUILD6, T1-T2 |
| Meko feature proposal | 10 | Originality, actual build friction, feasibility, and impact. | D3, F1-F6 |
| Build in public | 5 | Qualifying LinkedIn project post. | P1 |
| **Base total** | **100** | Bonus points may be added for build in public. | P2 |

**RECOMMENDED prioritization:** make the context-dependent story work, then verify visible context and the demo. Meko's role and execution together account for 55 base points. Collect build decisions throughout development; they cannot honestly be reconstructed at the end.

## 8. Technical guidance and practical constraints

These notes help implementation; they do not select a stack or add competition deliverables.

- **Meko connection:** the documented MCP endpoint is `https://mcp.mekodata.ai/mcp`. Tool calls select a datapack using its identifier. Follow the relevant client's current integration instructions. [S4: [Datapacks](https://docs.mekodata.ai/architecture/core-concepts/datapacks/), [Integrations](https://docs.mekodata.ai/integrations/)]
- **Tool schemas and editing:** verify the deployed MCP schema before coding. The reference lists operations for memory updates and deletion, with writer-identity restrictions. Promotion moves content to shared knowledge; do not assume a private-memory delete also removes promoted content. [S4: [MCP reference](https://docs.mekodata.ai/reference/mcp-server/)]
- **Extraction timing:** conversation-driven extraction is asynchronous and best-effort, so a saved conversation is not proof that the required fact is already retrievable. Verify recall and use an explicit memory operation when needed. [S4: [Memory](https://docs.mekodata.ai/architecture/core-concepts/memory/)]
- **Sharing semantics:** the May blog describes learning promotion as automatic; the challenge requires promoted build decisions, and current documentation describes review and explicit promotion. Use the explicit documented flow and verify teammate recall. Promotion shares within a datapack, not automatically across datapacks. [S1, p. 2; S3; S4: [Learnings](https://docs.mekodata.ai/architecture/core-concepts/learnings/)]
- **Model choice:** choose a model with reliable tool/function calling for agent workflows. Function calling means the model can request a software tool operation; merely producing structured text is not equivalent to executing a multi-step workflow. The brief treats structured output alone as sufficient only for single-step calls. Hosted and open models are allowed. [S1, p. 5]
- **Connectivity:** Meko is online, and hosted models also require internet. The brief says the event can arrange at most one connection per team and advises bringing a hotspot. If using a local open model, download its trained model files before the event. [S1, pp. 1, 5]
- **Accounts and docs:** the brief provides a Meko account for each teammate and directs teams to the quick start, core concepts, examples, and tool documentation. Confirm access early. [S1, p. 1; [S4](https://docs.mekodata.ai/)]

This requirements file does not establish working product behavior. Consult the [architecture and verification limits](docs/architecture.md) for actual checks. Slack installation, fresh human message intake, outbound replies and fresh-account Meko conversation capture have live checks. External action tools, demo timing, and challenge acceptance remain pending.

## 9. Scope boundaries: what Track A does not require

Do not import these into the mandatory backlog without a product reason:

| Item | Track A position | Source |
| --- | --- | --- |
| Campus grievance system | Track B's assigned problem; Track A chooses its own app. | S1, pp. 1-3 |
| Live swarm board and every-call visualization | Required for Track B. Track A instead requires A4's visible recalled/stored context and user controls. | S1, pp. 2-4 |
| At least two product agents | Track B's minimum. Track A does not state a minimum product-agent count. This is separate from T1's two teammates' coding agents. | S1, pp. 2, 4 |
| One-page design note | Listed as a Track B submission, not a Track A submission. | S1, p. 1 |
| Open-source or laptop-hosted LLM | Track B has a dedicated ten-point category. Track A has no corresponding model-choice category. | S1, pp. 4-5 |
| User login, mobile app, or real external APIs | Explicitly not needed. Choose only if the product benefits. | S1, p. 1 |
| Particular language or framework | Explicitly not prescribed. | S1, p. 1 |
| All six A2 capabilities | At least three are required; the other categories are optional. | S1, p. 2 |
| A prescribed product datapack layout | The department-agent diagram is a Track B example. Track A still must separate build and product data. | S1, p. 2 |
| Self-hosting Meko or administering YugabyteDB | Neither is listed as a requirement; Meko account/tool usage is the brief's integration path. | S1, pp. 1-2 |
| Training or fine-tuning a model | Not listed as a requirement. Meko-based recall supplies context to an agent; it does not by itself establish any change to model weights. | S1, pp. 1-2, 5 |

## 10. Decisions and organizer clarifications still open

These are unresolved details, not reasons to stop other work.

| ID | Type | Open question | Why it matters |
| --- | --- | --- | --- |
| O1 | Team decision | What is the persona, problem, and single context-dependent story? | Defines A1 and A3 and bounds the app. |
| O2 | Verification pending | Which candidate capabilities does the running demonstration prove? | The earlier fixed selection is superseded; product design is approved. Claim actual delivered uses. |
| O3 | Team decision | What is the team name, who owns `<team>-build`, and which teammates/agents contribute? | Enables shared access, attribution, and Check T. |
| O4 | Partly settled | Separate datapacks and a model-based Slack chunk router are approved. Installed employees automatically follow channel invitations. | Verify actual routing and human event handling; optional test channel limits must not become onboarding steps. |
| O5 | Partly settled | OpenAI, the existing OpenHuman UI, and a small tool loop are selected. Which concrete model and demo timing work best? | Verify real model/tool behaviour once the key is configured. |
| O6 | Organizer clarification | What are the submission portal, exact deadline, required links/form fields, and repository visibility rules? | The brief gives deliverables but no submission mechanics or public-repository requirement. |
| O7 | Organizer clarification | Are the product demo, Check T, and feature pitch timed separately? Is a recorded product demo acceptable? | Five-minute product and three-minute proposal-video limits are given, but combined timing and recording rules are not. |
| O8 | Organizer clarification | How are setup commands counted, including checkout, credentials, dependencies, and manual provisioning? | No detailed counting convention is specified. Keep prerequisites transparent. |
| O9 | Organizer clarification | Who should receive judge Viewer invitations, and by when? | Needed to complete BUILD6. |
| O10 | Organizer clarification | How are LinkedIn bonus points calculated, and are particular tags or hashtags expected? | The brief specifies mentions and likes by judging time, but no formula, tag handles, or hashtags. |
| O11 | Organizer clarification if needed | Are there additional Track A rules for seeded history, simulation, outages, or demo fallback recordings? | Explicit seeded-history and every-step-live instructions appear in Track B. Do not assume they settle Track A's policy. |

## 11. Final readiness checklist

This is an index of the requirements above. Checking a box requires evidence; no boxes are pre-completed.

- [ ] E1-E3: eligibility, event timeline, and separate hackCBS rules checked.
- [ ] BUILD1-BUILD3: every teammate's coding agent is connected with their own key; shared build datapack and repository protocol are in use.
- [ ] BUILD4-BUILD5: build/product datapacks are separate; build records contain no keys or unrelated personal data.
- [ ] BUILD6: judges invited as Viewers.
- [ ] T1: at least ten promoted decisions from at least two teammates' coding agents, with teammate attribution on each.
- [ ] T2: live cross-teammate Check T succeeds through Meko.
- [ ] A1: same flow produces a clearly different useful outcome with Meko on and off.
- [ ] A2: at least three qualifying product uses are demonstrated and justified.
- [ ] A3: one persona, problem, and demo story are clear.
- [ ] A4: recalled/stored context is visible and correction/forget controls work.
- [ ] A5: context displays are backed by Meko responses and data is limited to the story's needs.
- [ ] D1: repository README setup verified in five commands or fewer.
- [ ] D2: product demo rehearsed within five minutes.
- [ ] D3, F1-F6: feature proposal complete, including real build evidence and proposed call/response.
- [ ] P1, if pursuing public-build points: LinkedIn post includes the demo, Meko's role, and all three required mentions.
- [ ] O6-O11: organizer-dependent details resolved where needed for submission.
