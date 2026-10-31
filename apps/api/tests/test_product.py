from uuid import uuid4

import pytest

from tests.conftest import setup_company


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
