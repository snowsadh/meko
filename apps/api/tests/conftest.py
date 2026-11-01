"""Real database/API checks with a documented-shape Meko fake and a model stub.

No credentials, Slack messages, or remote Meko datapacks are used by these tests.
"""

import hashlib
import os
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.agent import build
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.meko import MekoError, meko
from app.main import app


class FakeMeko:
    def __init__(self):
        self.facts = {}
        self.files = {}
        self.calls = []
        self.captures = {}
        self.fail_search = False
        self.fail_file_delete = False
        self.datapacks = {}

    async def ensure_datapack(self, name, description):
        if name in self.datapacks and self.datapacks[name] != description:
            raise MekoError("That datapack name is already in use.")
        self.datapacks[name] = description
        return str(uuid5(NAMESPACE_URL, name))

    async def conversation(self, pack, agent, session, title):
        return uuid5(NAMESPACE_URL, pack + session).hex

    async def list_memories(self, pack, page=1, limit=25, query=None):
        rows = list(self.facts.get(pack, {}).values())
        if query:
            rows = [row for row in rows if query.casefold() in row["data"].casefold()]
        return {
            "memories": rows[(page - 1) * limit : page * limit],
            "total": len(rows),
            "page": page,
            "total_pages": max(1, (len(rows) + limit - 1) // limit),
        }

    async def upload(self, pack, filename, content):
        key = f"owner/{pack}/{hashlib.sha256(content).hexdigest()}/{filename}"
        identifier = str(uuid5(NAMESPACE_URL, key))
        self.files.setdefault(pack, {})[identifier] = {
            "id": identifier,
            "document_name": key,
            "key": key,
            "content": content.decode(),
            "status": "COMPLETED",
        }
        return {"document_key": key, "status": "processing"}

    async def document_status(self, pack, key):
        return {"document_status": "COMPLETED"}

    async def documents(self, pack, page=1):
        return {"items": list(self.files.get(pack, {}).values()), "has_more": False}

    async def delete_document(self, pack, identifier):
        if not self.fail_file_delete:
            self.files[pack].pop(identifier)
        return {
            "document_id": identifier,
            "chunks_deleted": 1,
            "s3_deleted": not self.fail_file_delete,
        }

    async def delete_pack(self, pack):
        self.facts.pop(pack, None)
        self.files.pop(pack, None)

    async def call(self, name, *, datapack_id, **args):
        self.calls.append((name, datapack_id, args))
        facts = self.facts.setdefault(datapack_id, {})
        if name in {"memory_search", "knowledgebase_search"} and self.fail_search:
            raise MekoError("Search unavailable")
        if name == "memory_search":
            rows = list(facts.values())
            if args.get("run_id"):
                rows = [row for row in rows if row["conversation_id"] == args["run_id"]]
            return {"results": rows}
        if name == "knowledgebase_search":
            return {
                "results": [
                    {"id": row["id"], "document_id": row["id"], "chunk_text": row["content"]}
                    for row in self.files.get(datapack_id, {}).values()
                ]
            }
        if name == "memory_add":
            identifier = str(uuid4())
            row = {
                "id": identifier,
                "data": args["text"],
                "agent_id": args["agent_id"],
                "conversation_id": args["conversation_id"],
            }
            facts[identifier] = row
            return {"results": [row]}
        if name == "memory_update":
            facts[args["memory_id"]]["data"] = args["text"]
            return {"status": "success"}
        if name == "memory_delete_by_id":
            facts.pop(args["memory_id"])
            return {"status": "success"}
        if name == "conversation_add_message":
            self.captures[args["seed"]] = (datapack_id, args)
            return {"status": "success"}
        if name == "conversation_get":
            requested = args["conversation_id"]
            rows = [
                turn
                for pack, turn in self.captures.values()
                if pack == datapack_id and turn["conversation_id"] == requested
            ]
            return {"messages": rows, "message_count": len(rows)}
        raise AssertionError(name)


class StubModel:
    def __init__(self):
        self.messages = []

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        self.messages.append(list(messages))
        return AIMessage(content="A model stub reply for the request.")


@pytest_asyncio.fixture
async def product(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable database ending in _test.")
    if not url.split("?")[0].endswith("_test"):
        raise RuntimeError("Refusing to reset a database whose name does not end in _test")
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = db
    fake = FakeMeko()
    for name in [
        "ensure_datapack",
        "conversation",
        "list_memories",
        "upload",
        "document_status",
        "documents",
        "delete_document",
        "delete_pack",
        "call",
    ]:
        monkeypatch.setattr(meko, name, getattr(fake, name))
    monkeypatch.setattr(build, "async_session_factory", factory)
    model = StubModel()
    monkeypatch.setattr(build, "ChatOpenAI", lambda **kwargs: model)
    monkeypatch.setattr(settings, "openai_api_key", "synthetic-test-key")
    # Local operator settings must not restrict synthetic channels or open real sockets.
    monkeypatch.setattr(settings, "gateway_enabled", False)
    monkeypatch.setattr(settings, "slack_memory_enabled", True)
    monkeypatch.setattr(settings, "slack_allowed_channel_ids", [])
    monkeypatch.setattr(settings, "slack_identity_mode", "fixed")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, fake, model
    app.dependency_overrides.clear()
    await engine.dispose()


async def setup_company(client, suffix="one"):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": f"{suffix}@example.com",
            "password": "test-password-123",
            "name": "Test Operator",
        },
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert (await client.get("/api/organizations", headers=headers)).json() == []
    response = await client.post(
        "/api/organizations", headers=headers, json={"name": "Test Company"}
    )
    assert response.status_code == 201, response.text
    org = response.json()
    employees = []
    for kind, name in [("support", "Alex"), ("hr", "Alison")]:
        response = await client.post(
            f"/api/organizations/{org['id']}/employees",
            headers=headers,
            json={"name": name, "employee_type": kind},
        )
        assert response.status_code == 201, response.text
        employees.append(response.json())
    return headers, org, *employees
