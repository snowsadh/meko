from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.core.config import settings
from app.core.meko import MekoClient, MekoError, meko
from app.memory.scopes import connect_employee, datapack_name


@pytest.mark.asyncio
async def test_onboarding_names_and_existing_ids(monkeypatch):
    ids = [str(uuid4()) for _ in range(3)]
    ensure = AsyncMock(side_effect=ids)
    monkeypatch.setattr(meko, "ensure_datapack", ensure)
    db = SimpleNamespace(commit=AsyncMock())
    company = SimpleNamespace(id=uuid4(), name="Atlas", meko_datapack_id=None)
    alex = SimpleNamespace(id=uuid4(), name="Alex", meko_datapack_id=None)
    allison = SimpleNamespace(id=uuid4(), name="Allison", meko_datapack_id=None)
    await connect_employee(db, company, alex)
    await connect_employee(db, company, allison)
    assert [call.args[0] for call in ensure.call_args_list] == [
        "atlas-company-common", "alex-atlas-emp", "allison-atlas-emp",
    ]
    assert [company.meko_datapack_id, alex.meko_datapack_id, allison.meko_datapack_id] == ids
    await connect_employee(db, company, alex)
    assert ensure.await_count == 3
    assert datapack_name("  Atlas & Co. ", "Alex Smith") == "alex-smith-atlas-co-emp"
    for company_name in ["!!!", "a" * 60]:
        with pytest.raises(MekoError):
            datapack_name(company_name)


@pytest.mark.asyncio
async def test_datapack_lookup_only_reuses_matching_description(monkeypatch):
    monkeypatch.setattr(settings, "meko_product_api_key", "synthetic-test-key")
    pack = str(uuid4())

    def response(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"data": {"items": [{
            "datapack_id": pack, "datapack_name": "atlas-company-common",
            "grant": "owner", "description": "Company ID: one",
        }]}})

    client = MekoClient(transport=httpx.MockTransport(response))
    assert await client.ensure_datapack("atlas-company-common", "Company ID: one") == pack
    with pytest.raises(MekoError, match="already in use"):
        await client.ensure_datapack("atlas-company-common", "Company ID: two")
