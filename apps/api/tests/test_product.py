"""Real database/API checks with a documented-shape Meko fake and a model stub.

No credentials, Slack messages, or remote Meko datapacks are used by these tests.
"""

import hashlib
import os
from uuid import uuid4, uuid5, NAMESPACE_URL

import httpx
import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.core.meko import meko, MekoError
from app.agent import build


class FakeMeko:
    def __init__(self):
        self.facts = {}
        self.files = {}
        self.calls = []
        self.captures = {}
        self.fail_search = False
        self.fail_file_delete = False

    async def ensure_datapack(self, name, description):
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


@pytest.mark.asyncio
async def test_private_context_publication_correction_and_forget(product):
    client, fake, _ = product
    headers, org, support, hr = await setup_company(client)
    base = f"/api/organizations/{org['id']}"
    assert len({org["meko_datapack_id"], support["meko_datapack_id"], hr["meko_datapack_id"]}) == 3
    assert support["duties"] and support["auto_memory"] is True
    text = "Atlas login incidents are assigned to Maya."
    result = await client.post(
        base + "/memory/facts", headers=headers, json={"employee_id": support["id"], "text": text}
    )
    assert result.status_code == 200, result.text
    memory_id = result.json()["facts"][0]["id"]
    response = await client.post(
        base + "/memory/search",
        headers=headers,
        json={"employee_id": hr["id"], "query": "Who handles login issues?"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == []
    # Publishing requires confirmation of the exact current text.
    response = await client.post(
        base + f"/memory/facts/{memory_id}/share",
        headers=headers,
        json={"employee_id": support["id"], "expected_text": "stale text", "confirmed": True},
    )
    assert response.status_code == 409
    response = await client.post(
        base + f"/memory/facts/{memory_id}/share",
        headers=headers,
        json={"employee_id": support["id"], "expected_text": text, "confirmed": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["scope"] == "org"
    listing = await client.get(base + "/memory-sources", headers=headers)
    assert listing.json()[0]["status"] == "indexed", listing.text
    response = await client.post(
        base + "/memory/search",
        headers=headers,
        json={"employee_id": hr["id"], "query": "Who handles login issues?"},
    )
    assert any(
        text in hit["content"] and hit["container_tag"] == "company_document"
        for hit in response.json()["results"]
    )
    response = await client.patch(
        base + f"/memory/facts/{memory_id}",
        headers=headers,
        json={"employee_id": support["id"], "text": "Atlas login incidents are assigned to Noor."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["withdrawn_shared_copies"] == 1
    assert fake.files[org["meko_datapack_id"]] == {}
    response = await client.delete(
        base + f"/memory/facts/{memory_id}", headers=headers, params={"employee_id": support["id"]}
    )
    assert response.status_code == 200, response.text
    assert fake.facts[support["meko_datapack_id"]] == {}
    # Another authenticated account cannot view or edit the first company's context.
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "other@example.com",
            "password": "another-password",
            "name": "Other Operator",
        },
    )
    other = {"Authorization": "Bearer " + response.json()["access_token"]}
    response = await client.get(base + f"/employees/{support['id']}/memories", headers=other)
    assert response.status_code == 404
    assert (
        await client.post(
            "/api/slack/install", json={"org_id": org["id"], "employee_id": support["id"]}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/slack/install",
            headers=other,
            json={"org_id": org["id"], "employee_id": support["id"]},
        )
    ).status_code == 404
    for path in ("/api/activity", "/api/activity/stats"):
        response = await client.get(path, headers=other, params={"organization_id": org["id"]})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_capture_comparison_dedup_and_search_failure(product):
    client, fake, model = product
    headers, org, support, _ = await setup_company(client)
    base = f"/api/organizations/{org['id']}"
    await client.post(
        base + "/memory/facts",
        headers=headers,
        json={"employee_id": support["id"], "text": "The internal routing contact is Maya."},
    )
    request = {
        "org_id": org["id"],
        "employee_id": support["id"],
        "message": "Who handles login problems?",
        "request_key": str(uuid4()),
        "thread_key": "same-thread",
    }
    response = await client.post("/api/agent/message", headers=headers, json=request)
    assert response.status_code == 200, response.text
    run_id = response.json()["id"]
    assert response.json()["recalled"]
    assert len(fake.captures) == 1
    assert next(iter(fake.captures.values()))[0] == support["meko_datapack_id"]
    response = await client.post("/api/agent/message", headers=headers, json=request)
    assert response.json()["id"] == run_id and len(fake.captures) == 1
    call_count = len(fake.calls)
    response = await client.post(
        "/api/agent/message",
        headers=headers,
        json={**request, "request_key": str(uuid4()), "use_meko": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["recalled"] == [] and response.json()["capture_status"] == "skipped"
    assert len(fake.calls) == call_count
    assert "internal routing contact" not in str(model.messages[-1])
    fake.fail_search = True
    model_calls = len(model.messages)
    response = await client.post(
        "/api/agent/message", headers=headers, json={**request, "request_key": str(uuid4())}
    )
    assert response.status_code == 502 and "Search unavailable" in response.text
    assert len(model.messages) == model_calls


@pytest.mark.asyncio
async def test_document_scope_and_unconfirmed_delete(product):
    client, fake, _ = product
    headers, org, support, hr = await setup_company(client)
    base = f"/api/organizations/{org['id']}"
    response = await client.post(
        "/api/documents",
        headers=headers,
        data={"organization_id": org["id"], "employee_id": support["id"]},
        files={
            "file": ("support.md", b"# Support\nEscalate Atlas issues to Maya.", "text/markdown")
        },
    )
    assert response.status_code == 201, response.text
    source_id = response.json()["id"]
    await client.get(base + "/memory-sources", headers=headers)
    response = await client.post(
        base + "/memory/search", headers=headers, json={"employee_id": hr["id"], "query": "Atlas"}
    )
    assert response.json()["results"] == []
    fake.fail_file_delete = True
    response = await client.delete(base + f"/memory-sources/{source_id}", headers=headers)
    assert response.status_code == 502
    listing = await client.get(base + "/memory-sources", headers=headers)
    assert listing.json()[0]["error_message"]
