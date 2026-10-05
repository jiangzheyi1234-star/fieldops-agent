import asyncio

import pytest

from fieldops.agent import diagnose, validate_plan
from fieldops.api import create_app
from fieldops.fixtures import make_fixture
from fieldops.models import RepairPlan
from fieldops.store import Store


def test_model_plan_requires_grounded_evidence_and_contract_values():
    async def exercise():
        store = Store(":memory:")
        app = create_app(store)
        item = store.create(make_fixture("dimension", 201), "offline")
        item = await diagnose(app, store, item["id"])
        raw = item["plan"]
        raw["actions"][0]["value"] = 1
        with pytest.raises(ValueError, match="contract"):
            validate_plan(item, RepairPlan.model_validate(raw))
        raw["actions"][0]["value"] = item["contract"]["embedding_dim"]
        raw["actions"][0]["evidence_ids"] = ["invented"]
        with pytest.raises(ValueError, match="evidence"):
            validate_plan(item, RepairPlan.model_validate(raw))
        store.close()

    asyncio.run(exercise())
