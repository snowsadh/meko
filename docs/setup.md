# Setup and development

The [README](../README.md#setup-in-five-steps) covers the five-step local setup. This guide has the Slack configuration, available tools and development checks.

## Running locally

The first YugabyteDB image download is large. Application data persists in the Docker Compose volume. Meko memory and knowledge live in the configured Meko service.

After editing `.env`, apply the changes with:

```sh
docker compose up -d --force-recreate backend
```

The backend's `/ready` endpoint checks the application database and key presence; it does not verify remote service connectivity. Keep keys in `.env`, which is ignored by Git.

## Slack setup

1. Configure each required role's Slack app credentials in `.env`. Enable Socket Mode and create an app-level token with `connections:write`.
2. Set `SLACK_OAUTH_REDIRECT_URI` to the backend's public HTTPS URL ending in `/api/slack/oauth/callback`. Register that exact URL under each Slack app's OAuth & Permissions. Local development needs an HTTPS tunnel or a deployed backend for this callback. [Slack requires HTTPS for OAuth redirects](https://docs.slack.dev/authentication/installing-with-oauth/).
3. Subscribe to bot events `app_mention`, `message.channels`, `message.groups`, `message.im`, and `message.mpim`. Requested bot scopes are `app_mentions:read`, `channels:history`, `groups:history`, `chat:write`, `im:history`, `im:write`, and `mpim:history`.
4. Recreate the backend after server credential changes. In the employee's configuration page, choose **Add [name] to Slack**, finish Slack's approval, and invite that employee to the intended channels. One company uses one Slack workspace; fixed role apps each represent one employee in that workspace.
5. Mention the employee, send a direct message, or continue its thread. Its backend handles the request automatically. New channel invitations do not require a new listener, a channel ID setting or a server restart.

Slack connections and routed memory delivery are enabled by default. `GATEWAY_ENABLED=false` deliberately pauses Slack processing; `SLACK_MEMORY_ENABLED=false` records routing decisions without delivering them to Meko. These are server controls, not employee onboarding steps.

An app-level token opens one event connection per role app, covering its installed workspaces and channel memberships. Installation supplies the separate bot token used by the backend to send replies. OpenAI, employee instructions and Meko determine the answer; the Slack token supplies the sender identity. Socket Mode does not require a public event webhook. The collapsed **Work and context** section shows the actual connection state, routing previews, original chat, decisions and confirmed destination status. A routing preview uses OpenAI and writes nothing to Meko.

For local OAuth, run `python3 scripts/slack_callback_proxy.py` and, in another terminal, `cloudflared tunnel --url http://127.0.0.1:8010`. Register the printed HTTPS URL plus `/api/slack/oauth/callback` in Slack and set the same value in `.env`. This proxy exposes only that callback; other paths return 404. Its check is `python3 scripts/test_slack_callback_proxy.py`. The temporary URL changes when the tunnel restarts. Docker disables request access logs so OAuth codes and state are not recorded in request URLs.

For a bounded Slack test, set `SLACK_ALLOWED_CHANNEL_IDS=["C_YOUR_TEST_CHANNEL_ID"]`. Messages outside this list are ignored, and queued replies outside it are cancelled. Leave it empty to use all channels the installed bots can see. Recreate the backend after changing it.

If you cannot edit an existing Slack app, its owner can add you as a collaborator, or you can [create your own app](https://api.slack.com/apps?new_app=1). To fill its settings in one paste, run `python3 scripts/slack_manifest.py --name Alex --callback https://YOUR_TUNNEL/api/slack/oauth/callback`, then choose **From a manifest**, select **JSON**, and paste the output. This configures the required bot permissions, events, direct messages and Socket Mode. From **Basic Information**, copy the Client ID and Client Secret; generate an app-level token with `connections:write`. Set the three `SLACK_BOT_SUPPORT_*` values in `.env`, recreate the backend, and use **Add Alex to Slack** on the employee page. Repeat with the other roles' names and environment prefixes only when needed. See [Slack's manifest guide](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/).

## Employee actions

On an employee's page, connect **Exa Web Search**, **Pitch Deck Generator**, or **Visualization Charts**. These need no extra credentials. Search uses [Exa's public MCP service](https://exa.ai/docs/get-started/exa-mcp), whose service rate limits apply. Presentations and bar charts are generated locally; they do not use Canva or Gamma.

Ask in Slack for a PowerPoint, a chart from supplied numbers, or public web research. The website's **Work and context → Chat** also supports these actions when **Allow connected tools for this request** is checked. It is off by default. Successful file tools return a download link; sign in to the company account to download. Files are stored privately with the originating run, not published to company knowledge automatically.

n8n connections require the real HTTPS MCP endpoint and token, and tool discovery must succeed before saving. Other catalogue entries are not implemented connections yet.

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

`scripts/check_meko.py` is a live, synthetic-data check. It reuses two demo datapacks because deleted datapacks do not restore creation-quota slots. Run it only with an approved account and available quota. Stop on quota errors; do not repeatedly retry them. On 2026-11-01, conversation saving, automatic extraction and fresh-task recall passed against the newly authorised account through the local application API.

The employee page's **Work and context → Chat** can compare Meko enabled/disabled. Disabling saved knowledge bypasses Meko and old thread history. Connected work tools are controlled separately by the explicit checkbox, which is off by default.

`scripts/check_dashboard_auth.py` uses Playwright against the running app to check missing-cookie recovery, invalid saved sessions, cookie-only sessions and fresh sign-in. Supply an existing test account through `OPENHUMAN_TEST_EMAIL` and `OPENHUMAN_TEST_PASSWORD`, then run `uv run --project apps/api --with playwright python scripts/check_dashboard_auth.py`. Install Playwright's Chromium first if needed. The check makes no Meko calls and does not reset a database.

See [architecture](architecture.md), [challenge requirements](../requirements.md), and [Meko notes](meko-notes.md).
