# OpenHuman architecture

A company creates a workspace, adds optional shared documents, hires employees from job templates, customises their instructions and documents, and connects them to Slack. The website manages their settings and shows actual memory and activity.

## Storage and access

YugabyteDB stores accounts, companies, employee configuration, source records and activity. Meko stores employee context and shared company knowledge. The server authorises company ownership before selecting a datapack. No product request can use the build or default datapack.

Each employee reads its own memories/documents plus company knowledge. Separate datapacks prevent one employee from retrieving another employee's private context. The company administrator can inspect employee configuration and memory.

## Slack and reasoning

Slack apps use Socket Mode and signed installation state. The server routes events by workspace and job type, deduplicates events, and keeps replies in the correct thread. OpenAI receives the job baseline, company details, custom instructions, relevant evidence and permitted tools. Only successful tool results justify completed-action claims.

## Approved chat-router policy

One company router batches Slack messages into chunks and asks OpenAI where each chunk belongs: company knowledge, one or more employees, both, or neither. The server checks returned employee IDs against the company roster and records the choice and evidence. Meko handles durable-fact extraction after an employee conversation is accepted.

The routing policy is approved; implementation and Slack verification follow the initial checkpoint. Channel boundaries, deduplication and failures must stay visible. Do not turn unrelated workspace traffic into company knowledge.

## Verification limits

Company/employee setup, memory boundaries and mutations have backend checks with service stubs. Real Meko fact/document operations and a real OpenAI reply/local-tool call were checked. Conversation capture hit the current account's lifetime quota. Live Slack and external workflow execution still require credentials and an authorised test channel.
