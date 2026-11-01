# OpenHuman

AI employees for a company, working in Slack with Meko memory and company knowledge.

Create a company, optionally upload shared documents, choose an employee from a job template, customise their duties/instructions, add relevant documents, and connect Slack. The website manages employees, knowledge, remembered facts and actual activity.

## Run

Requires Docker with Compose, Python 3, an OpenAI key and a Meko product key.

1. Run `python3 scripts/setup.py`.
2. Add `OPENAI_API_KEY` and `MEKO_PRODUCT_API_KEY` to the root `.env`.
3. Run `docker compose up --build -d`.
4. Open [localhost:3000](http://localhost:3000).

The first YugabyteDB image download is large. Data persists in the Compose volume. `/ready` checks the application database and key presence, not remote service connectivity. After editing `.env`, run `docker compose up -d --force-recreate backend`.

Slack stays off until its app credentials are configured. `.env.example` lists the per-role Slack app settings. Use a private test channel first. No keys belong in chat, logs, source control or Meko memory.

## Slack setup

1. Configure each required role's Slack app credentials in `.env`. Enable Socket Mode and create an app-level token with `connections:write`.
2. Set `SLACK_OAUTH_REDIRECT_URI` to the backend's public HTTPS URL ending in `/api/slack/oauth/callback`. Register that exact URL under each Slack app's OAuth & Permissions. Local development needs an HTTPS tunnel or a deployed backend for this callback. [Slack requires HTTPS for OAuth redirects](https://docs.slack.dev/authentication/installing-with-oauth/).
3. Subscribe to bot events `app_mention`, `message.channels`, `message.groups`, `message.im`, and `message.mpim`. Requested bot scopes are `app_mentions:read`, `channels:history`, `groups:history`, `chat:write`, `im:history`, `im:write`, and `mpim:history`.
4. Recreate the backend after environment changes. In the employee's configuration page, choose **Connect Slack**, finish Slack's approval, and invite that employee to the intended channels. One company uses one Slack workspace; fixed role apps each represent one employee in that workspace.
5. Set `GATEWAY_ENABLED=true` and recreate the backend when ready to listen and reply. Keep `SLACK_MEMORY_ENABLED=false` while the Meko account lacks conversation quota. Enable it after valid product scopes and quota are available.

An app-level token opens the event connection; installation supplies the separate bot token used to reply. Socket Mode does not require a public event webhook. The collapsed **Work and context** section shows app setup, routing previews, original chat, decisions and actual destination status. A routing preview uses OpenAI and writes nothing to Meko.

For local OAuth, run `python3 scripts/slack_callback_proxy.py` and, in another terminal, `cloudflared tunnel --url http://127.0.0.1:8010`. Register the printed HTTPS URL plus `/api/slack/oauth/callback` in Slack and set the same value in `.env`. This proxy exposes only that callback; other paths return 404. Its check is `python3 scripts/test_slack_callback_proxy.py`. The temporary URL changes when the tunnel restarts. Docker disables request access logs so OAuth codes and state are not recorded in request URLs.

## How memory works

- One company datapack holds shared knowledge; each AI employee has a separate datapack for private documents and memory.
- Before answering, an employee searches its own context and company knowledge.
- A Slack chat router uses OpenAI to choose whether a chunk belongs to company knowledge, selected employees, both, or neither. Meko handles fact extraction for conversations sent to employee memory.
- The website shows actual sources and remembered facts, supports remember/correct/forget, and records evidence and tool results. Conversation capture and asynchronous fact extraction have separate status.
- Application accounts, configuration and activity live in local YugabyteDB. Meko uses its configured service endpoint. OpenAI handles replies and model-directed tool calls.

The default Meko datapack is forbidden. Build-team context belongs only in the explicitly named build datapack; application data uses its separate product scopes.

## Development

Install Bun 1.3.10+ and `uv`, then run `bun install` and `uv sync --project apps/api --extra dev`. Start the database with `docker compose up -d database`.

From `apps/api`, set `DATABASE_URL=postgresql+asyncpg://yugabyte:yugabyte@localhost:5433/yugabyte`, run `uv run alembic upgrade head`, then `uv run uvicorn app.main:app --reload`. From `apps/web`, run `bun run dev`.

```sh
bun run typecheck
bun run build
uv run --project apps/api python scripts/check_slack_router.py
```

The routing check above makes real OpenAI calls using synthetic chat. It makes no Slack or Meko calls. Outcomes are model decisions, not a guarantee of classification accuracy.

Backend checks require a disposable database whose name ends in `_test`. They reset that database's schema and use controlled service responses unless a live check is explicitly selected:

```sh
docker compose exec -T database bin/ysqlsh -h database -U yugabyte -d yugabyte -c 'CREATE DATABASE openhuman_test'
TEST_DATABASE_URL=postgresql+asyncpg://yugabyte:yugabyte@localhost:5433/openhuman_test uv run --project apps/api pytest apps/api/tests -q
```

`scripts/check_meko.py` is a live, synthetic-data check. It reuses two demo datapacks because deleted datapacks do not restore creation-quota slots. Run it only with an approved account and available quota. Conversation capture was blocked by the current account's lifetime request limit; do not repeatedly retry it.

The employee page's **Work and context** preview can compare Meko enabled/disabled. Disabled previews bypass Meko and old thread history; connected external work tools are disabled in the preview.

See [architecture](docs/architecture.md), [challenge requirements](requirements.md), and [Meko notes](docs/meko-notes.md).
