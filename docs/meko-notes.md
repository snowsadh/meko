---
status: documentation_review
reviewed_on: 2026-10-31
runtime_verification: pending
memory_upload: prohibited_for_this_private_exploration
---

# Meko: facts that shape our OpenHuman build

## Read this first

Meko can hold company documents and remembered lessons for OpenHuman's coworkers. We still build the coworkers' working flow, model calls, permissions, and actions. Meko does not run that product for us.

Coworkers running under one Meko account can recall each other's memories in the same datapack. That means agent IDs alone cannot provide the employee-specific private context the user wants. The revised design recommends separate employee datapacks plus a company knowledge datapack; the user still needs to settle that layout.

These notes describe the public service contract, not a completed integration. [openhuman-design.md](openhuman-design.md) turns them into a proposed product design.

## What was reviewed

Read the documentation site's reachable pages from its sitemap and internal navigation: **66 successful HTML URLs**, including onboarding, every core concept, guides, examples, integrations, references, troubleshooting, and the full published platform and installer release history. Also read `llms.txt` and inspected the public Datapack API OpenAPI contract. Some URLs are aliases rather than distinct articles.

[meko-docs-index.json](meko-docs-index.json) records URLs, content hashes, word counts, and six broken navigation targets. Raw extracts are kept locally in `/tmp/meko-full-review/`. The index establishes the review's coverage and date; it does not establish runtime correctness.

Current published release notes: platform 1.0.5, dated October 22; installer 2.5.1, dated October 28. Installer, skills, and server versions are independent. Older release notes explain changes; use current references for new calls. [Release tracks](https://docs.mekodata.ai/changelog/), [latest platform](https://docs.mekodata.ai/changelog/meko/v1.0.5/), [latest installer](https://docs.mekodata.ai/changelog/installer/v2.5.1/).

## 1. Where Meko sits

Our server calls the language model to do a task. Before that call, it asks Meko for relevant facts and document passages. It then gives that evidence to the model. Meko manages the search indexes and underlying YugabyteDB storage.

We cannot use that managed database as our app's ordinary SQL connection. Account records, coworkers, approvals, and task state still need application storage. The retired database tools in older release notes are not our integration path. [Architecture](https://docs.mekodata.ai/architecture/how-meko-fits/), [database-tool removal](https://docs.mekodata.ai/changelog/meko/v0.9.1/).

Meko is currently a managed cloud service. There is no released Meko Python SDK to assume exists; custom applications connect through the Model Context Protocol (MCP), a standard way to call service tools. The public HTTP API complements those tools for file and workspace management. [Programmatic integration](https://docs.mekodata.ai/integrations/connect-programmatically/), [agent-facing documentation](https://docs.mekodata.ai/llms.txt).

## 2. Four storage types with different jobs

| Type | What goes in | What comes back | OpenHuman use |
| --- | --- | --- | --- |
| Memory | Short, durable facts extracted from supplied text | Relevant facts with identifiers | Approved lessons from work |
| Knowledge-base file | Company documents | Indexed passages | Policies, product notes, runbooks |
| Conversation | Saved raw exchanges | Stored thread history | Optional; automatic extraction makes this a deliberate choice |
| Artifact | A complete file | Its original bytes, retrieved by content hash | Optional generated deliverables |

Uploading an artifact does not make its contents searchable. Adding a memory does not preserve the supplied text verbatim. These are different operations, not interchangeable storage names. [Storage guide](https://docs.mekodata.ai/guides/where-to-store/).

Projects and folders organize datapacks in the portal; they do not combine their knowledge or permissions. Deleting a project also deletes its contained datapacks. We do not need projects for the first product. [Projects](https://docs.mekodata.ai/architecture/core-concepts/projects/).

## 3. Identity, access, and sharing

**Datapack:** Meko's actual knowledge boundary. A caller supplies its identifier on each operation. One product company can have one datapack; the coding team uses a different build datapack.

**Authenticated account:** determined by the API key. A body field claiming a different user does not change that identity. Keys belong to accounts and can access all datapacks granted to that account; a new key is not automatically limited to one company. Keep the product key on our server and resolve the company's datapack there. [Keys](https://docs.mekodata.ai/reference/api-keys/), [HTTP authentication](https://docs.mekodata.ai/reference/datapack-api/#authenticate).

**Agent identifier:** records who wrote or used context. `memory_search` spans the authenticated account's agents within the chosen datapack. A different agent identifier does not create confidential coworker memory. Conversation fetch and memory modification have stricter ownership rules. [Memory](https://docs.mekodata.ai/architecture/core-concepts/memory/).

Meko calls unpromoted memory private, but other datapack members can see it through portal and API listing surfaces. Do not describe it as a secret vault. Separate confidential stores need separate datapacks and appropriate grants. [Datapacks](https://docs.mekodata.ai/architecture/core-concepts/datapacks/).

Roles:

- Viewers read; they cannot perform normal memory/conversation writes.
- Contributors can add memories, but cannot upload company knowledge or promote it.
- Maintainers and owners can upload knowledge and promote memories.
- Datapack rename and deletion are owner operations. Some deletion rights also follow the original author or uploader.

Check the operation's own contract; the roles are not interchangeable. [Access](https://docs.mekodata.ai/architecture/core-concepts/manage-access/), [sharing](https://docs.mekodata.ai/architecture/core-concepts/sharing/).

## 4. Recall is three different searches

`memory_search` retrieves the caller's facts across its agent identifiers. Its ranking combines meaning, exact terms, and named entities. The returned `score` determines order; cosine similarity is a different field. Use Meko's documented response scores for this implementation. [Retrieval](https://docs.mekodata.ai/architecture/core-concepts/memory-retrieval/).

`knowledgebase_search` retrieves shared document passages and promoted knowledge. It is not the same store as unpromoted memories. [Knowledge base](https://docs.mekodata.ai/architecture/core-concepts/knowledgebase/).

`context_search` combines memory, knowledge, and a conversation cache. Its conversation results may include other users' and agents' saved conversations in that datapack. Each source has its own status. In the revised employee/company layout, query the permitted memory and document stores explicitly so historical chat cannot bypass the intended scope. [Tool reference](https://docs.mekodata.ai/reference/mcp-server/#context-search).

Use bounded result counts and pass relevant evidence to the model. An error is not an empty store. Preserve both facts and document evidence instead of comparing unlike scores as if they measured the same thing.

`memory_get_all` returns a recent window, roughly 20 rows, without pagination. It cannot power a complete memory browser. The public HTTP memory list has pagination; exact IDs and ordinary search are also available. [Memory guide](https://docs.mekodata.ai/guides/working-with-memory/), [HTTP list](https://docs.mekodata.ai/reference/datapack-api/#list-memories-that-are-waiting).

## 5. Remembering is extraction, not a text insert

`memory_add` extracts durable facts from supplied text. A single request can produce a different number of facts than input sentences. Read back the actual facts and identifiers before claiming success.

Saving a turn with `conversation_add_message` also starts extraction, asynchronously and without guaranteeing every detail survives. The revised product intentionally uses eligible Slack turn capture for automatic employee memory. Our app decides which interactions to send and where; Meko extracts their durable facts. Company-wide publication remains separate. This supersedes the earlier proposal to require human review for every remembered fact. [Memory behavior](https://docs.mekodata.ai/architecture/core-concepts/memory/).

Use real conversation IDs returned by `conversation_create`. Its `session_id` supports stable deduplication, and the returned ID may be normalized into a 32-character trace identifier. Store it as text; do not assume every conversation ID is a hyphenated UUID. Agent and datapack identities must remain consistent across the operations.

The exposed schema says `memory_add.run_id` is trace metadata, not a stored memory filter. Conversation filtering uses `memory_search.run_id` with the stored conversation ID. Do not invent source filtering from arbitrary metadata. This detail came from the connected tool schema, rather than an app runtime test.

## 6. Promotion has a particular purpose

Promotion moves selected facts from an account's memory into shared knowledge within the **same datapack**. This lets a different Meko account retrieve them. It is a one-way move, not cross-datapack replication. Owners or maintainers review exact records and confirm before promotion. [Learnings](https://docs.mekodata.ai/architecture/core-concepts/learnings/).

The HTTP response can be successful while particular IDs were skipped. Inspect the inserted, updated, and not-found lists. An already moved ID can appear as not found on a repeat. Marking a fact to stay private also makes later promotion skip it. [Promotion API](https://docs.mekodata.ai/reference/datapack-api/#promote-memories).

Under one account and one datapack, cross-agent recall works without promotion, but does not give employees separate memory. With separate employee and company packs, publishing a lesson requires an explicit cross-pack copy; native promotion does not perform that transfer. Do not claim the copy is `memory_promote`. The challenge's **build-time** promoted-decision requirement still applies independently.

## 7. Correcting and forgetting need exact scope

Unpromoted facts have `memory_update` and `memory_delete_by_id`; callers must preserve the writing agent's identity. Track it alongside each fact. Test readback and subsequent searches before wiring a success message.

Promoted memory deletion is documented in the portal for new records, with a September 9, 2026 cutoff. The published contracts do not establish that our ordinary private-memory update/delete calls remove every promoted copy. Do not promise an untested endpoint. Cross-pack publication also creates a separate copy that needs explicit correction/removal tracking. [Memory controls](https://docs.mekodata.ai/guides/working-with-memory/#delete-a-memory).

Deleting a document removes its indexed chunks, but deletion is blocked during processing. The HTTP result distinguishes removed database rows from a stored object that could not be removed. Surface partial completion. [Document removal](https://docs.mekodata.ai/reference/datapack-api/#delete-an-uploaded-file).

Forget means removal from future active context in the stated store. Old task outputs and service traces are different records; do not promise an account-wide purge. If another file also contains the fact, identify that source rather than pretending one memory deletion removes it everywhere.

## 8. File ingestion is a complete workflow

The simplest backend path is HTTP multipart upload, followed by status polling. Keep both the upload key and the final document identifier: polling and deletion use different identifiers. A successful upload is not proof the document is searchable. Content hashes deduplicate identical bytes. [File API](https://docs.mekodata.ai/reference/datapack-api/#upload-a-file).

MCP uploads instead request a short-lived presigned POST, declare byte size and hash, supply an initial content sample, send the actual file, and poll completion. The request for a URL does not upload any bytes. It is useful for agents with files; our backend does not need to recreate this longer path. [File guide](https://docs.mekodata.ai/guides/working-with-knowledge-bases/).

Start with PDF, Markdown, and UTF-8 text. The current public upload call accepts file bytes, not a URL ingestion parameter. Defer website importing rather than assume Meko will crawl a pasted URL.

The Free plan documents 5 MB per file and 100 MB combined file/artifact storage. HTTP uploads have a 50 MB ceiling even on plans whose portal accepts larger files. Some artifact size wording differs between the guide and current tool/API reference; our first design does not depend on larger artifacts.

## 9. Connections, limits, errors, and observability

MCP endpoint: `https://mcp.mekodata.ai/mcp`. Public HTTP base: `https://api.mekodata.ai/api/v1`. Send `Authorization: Bearer <key>` and `User-Agent` on both. Use the existing MCP Python dependency and HTTP client, not an imagined Meko SDK.

Inspect MCP errors inside the returned payload as well as transport failures. Connected tools currently wrap their JSON result in a string. Normalize that once in our client. The public HTTP envelope uses `data` on success and an `error` object on failure. [HTTP errors](https://docs.mekodata.ai/reference/datapack-api/#read-errors).

Free-tier constraints include 10 lifetime datapack creations, 1,000 conversation-message calls, and 10,000 retrievals per month. Deleting a datapack does not recover a creation slot. This is a reason to provision stable company packs and reuse run identities, not repeatedly create test environments. Key-level HTTP rate limits are separate. Do not retry permissions or exhausted quotas as transient failures.

Traces reflect operations and information actually recorded. A model call made by our app does not automatically provide Meko with hidden model reasoning. Log tool results, source IDs, action outcomes, and short decision explanations if needed; never manufacture reasoning or evidence. Traces also do not prove an external action executed exactly once. [Observability](https://docs.mekodata.ai/guides/observability/), [trace example](https://docs.mekodata.ai/examples/trace-and-resume/).

WorkbenchLM is Meko's own document chat. Labs currently demonstrate code review. Our product needs a useful coworker task and controlled learning beyond duplicating those screens. [WorkbenchLM](https://docs.mekodata.ai/guides/workbench-lm/), [Labs](https://docs.mekodata.ai/examples/labs/).

Installer capture and repair are coding-client features, not something to install inside OpenHuman. This task's capture remains stopped to respect the user's opt-out. Do not resume or drain its backlog while testing product memory.

## 10. What still needs a real application check

The documentation review is complete; product behavior is not verified. Before building the full interface, test through the product runtime with synthetic content:

1. Employee A recalls its own fact; employee B cannot retrieve that private context through the app. After explicit company publication, B can find the published lesson.
2. The save response and exact readback expose enough identity to support correction and deletion, including extractor updates to existing facts.
3. Updating a fact changes later retrieval; deleting it prevents retrieval. Check both coworkers.
4. A document upload reaches completion, supplies a passage, and can be removed using its document ID.
5. Retrieval errors remain distinguishable from genuinely empty results.
6. A forged company/coworker choice cannot change the server-selected datapack.
7. Saving a participating Slack turn drives automatic extraction; the UI distinguishes pending extraction, actual facts, and unavailable source links.

These are verification gates, not reasons to build extra layers now. If a gate contradicts the public contract, discuss the concrete limitation before changing the product promise.
