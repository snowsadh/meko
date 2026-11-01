# OpenHuman architecture

A company creates a workspace, adds optional shared documents, hires employees from job templates, customises their instructions and documents, and connects them to Slack. The website manages their settings and shows actual memory and activity.

## Storage and access

YugabyteDB stores accounts, companies, employee configuration, source records and activity. Meko stores employee context and shared company knowledge. The server authorises company ownership before selecting a datapack. No product request can use the build or default datapack.

Each employee reads its own memories/documents plus company knowledge. Separate datapacks prevent one employee from retrieving another employee's private context. The company administrator can inspect employee configuration and memory.

## Slack and reasoning

Slack apps use Socket Mode (Slack's outgoing event connection) and signed installation state. One company is bound to one Slack workspace. The server saves intake before acknowledging events, deduplicates the same message across role apps and retries, and queues employee work separately. Direct messages, mentions and follow-ups in an employee's thread receive replies. Ordinary visible channel messages can feed the router without triggering a reply.

OpenAI receives the job baseline, company details, custom instructions, relevant evidence and permitted tools. Only successful tool results justify completed-action claims. Replies stay in the source thread and run in order for that employee/thread. An unconfirmed Slack send is recorded for inspection and is not automatically resent. Run one gateway process per deployment.

## Approved chat-router policy

One company router batches Slack messages into chunks and asks OpenAI where each chunk belongs: company knowledge, one or more employees, both, or neither. The server checks returned employee IDs against the company roster and records the choice and evidence. Meko handles durable-fact extraction after an employee conversation is accepted.

Chunks stay within their company, channel and thread and contain up to 12 messages after a 30-second batching window. The model selects short roster keys; the server maps those back to real employee IDs. It rejects destinations outside the eligible roster. Direct/group messages cannot go to company knowledge or unaddressed employees. The classifier receives the whole chunk; it is instructed to reject company publication if any part is sensitive. Semantic classification still depends on the model and can be wrong.

Employee destinations save the original chunk as a conversation in the employee's datapack. Meko then extracts durable facts asynchronously. Company destinations upload the original chunk as a Markdown knowledge document. Each destination records its real conversation/source ID. A chunk is complete only after its selected destinations confirm saving/indexing. Company indexing is checked no more often than every 30 seconds. Provider errors or indexing beyond 20 minutes stop automatic delivery; a deliberate retry skips completed destinations. Only the routed document is checked.

`SLACK_MEMORY_ENABLED=false` allows routing decisions to be recorded while all automatic Slack memory delivery waits. Disabling an employee's memory, suspending it, or changing its context version prevents an older queued decision from delivering there. Explicit requests to remember a fact still use the employee's private memory tool. Preview requests use the separate existing website capture path.

The employee page's collapsed **Work and context** section shows routing decisions, original messages, provider identifiers, errors and retry controls. Its routing preview calls OpenAI but sends nothing to Slack or Meko. The company administrator can inspect this company-wide log.

Slack history is collected from new events the installed bots can see, including the application's confirmed replies. There is no history backfill. Message edits, deletions and other apps' bot messages are currently ignored; changing a saved memory does not erase source transcripts or independently routed company documents. The company workspace binding remains after disconnecting an employee.

## Verification limits

Company/employee setup, memory boundaries, mutations, Slack event handling and delivery checkpoints have backend checks with service stubs against PostgreSQL and YugabyteDB. Real Meko fact/document operations and a real OpenAI reply/local-tool call were checked. Six synthetic routing examples matched expectations after prompt/roster fixes in a live OpenAI check; earlier checks exposed mistakes, so this is not an accuracy benchmark.

On 2026-11-01, two product datapacks were created on the newly authorised Meko account and connected to the local Atlas demo. A real website API task saved its conversation with readback; Meko extracted the escalation rule without a separate `remember_fact` call. A fresh task retrieved that private fact and the indexed company guide and named the correct escalation owner. The company memory store did not contain the private fact. This checks existing-company reconnection and fresh scope creation; it does not prove the full signup/onboarding flow on that account.

All five Slack app-level tokens passed `apps.connections.open`; no event listeners or live posts were used for that check. A temporary HTTPS callback has been prepared, with all other API paths excluded. Actual installation/reply verification still requires the owner to register that callback, grant Slack installation and authorise a test channel. `SLACK_ALLOWED_CHANNEL_IDS` can restrict intake and replies to that channel. Connected external services require their own real connections before workflow execution can be verified.
