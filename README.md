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
```

Backend checks require a disposable database whose name ends in `_test`. They reset that database's schema and use controlled service responses unless a live check is explicitly selected:

```sh
docker compose exec -T database bin/ysqlsh -h database -U yugabyte -d yugabyte -c 'CREATE DATABASE openhuman_test'
TEST_DATABASE_URL=postgresql+asyncpg://yugabyte:yugabyte@localhost:5433/openhuman_test uv run --project apps/api pytest apps/api/tests -q
```

`scripts/check_meko.py` is a live, synthetic-data check. It reuses two demo datapacks because deleted datapacks do not restore creation-quota slots. Run it only with an approved account and available quota. Conversation capture was blocked by the current account's lifetime request limit; do not repeatedly retry it.

The employee page's **Work and context** preview can compare Meko enabled/disabled. Disabled previews bypass Meko and old thread history; connected external work tools are disabled in the preview.

See [architecture](docs/architecture.md), [challenge requirements](requirements.md), and [Meko notes](docs/meko-notes.md).
