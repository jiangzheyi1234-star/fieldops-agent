"""Protocol tests use a fake provider; they are not live LLM quality evaluations."""

import asyncio
import json

import httpx
import pytest

from fieldops.agent import ToolSession, execute, llm_plan, validate_plan
from fieldops.api import create_app
from fieldops.fixtures import make_fixture
from fieldops.store import Store, digest


class ScriptedProvider:
    def __init__(self, invalid=False, **_):
        self.step = 0
        self.invalid = invalid

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def post(self, url, *, headers, json):
        assert url == "https://example.invalid/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key-never-real"
        assert len(json["tools"]) == 4
        sequence = [
            ("read_config", {}),
            ("probe_service", {}),
            ("search_runbooks", {"query": "embedding_dim VECTOR_DIMENSION_MISMATCH"}),
        ]
        if self.invalid:
            name, arguments = "bash", {"command": "not-allowed"}
        elif self.step < 3:
            name, arguments = sequence[self.step]
        else:
            import json as codec

            observation = codec.loads(next(m["content"] for m in json["messages"] if m["role"] == "tool"))
            dimension = observation["data"]["delivery_contract"]["embedding_dim"]
            name, arguments = (
                "submit_plan",
                {
                    "summary": "根据探测和手册修复维度配置。",
                    "unresolved": [],
                    "actions": [
                        {
                            "field": "embedding_dim",
                            "value": dimension,
                            "reason": "与交付清单一致",
                            "evidence_ids": ["E01", "E02", "E03"],
                            "runbook_id": "RB-DIM",
                        },
                    ],
                },
            )
        self.step += 1
        import json as codec

        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call-{self.step}",
                    "type": "function",
                    "function": {"name": name, "arguments": codec.dumps(arguments)},
                }
            ],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": message}], "usage": {"total_tokens": 100}},
            request=httpx.Request("POST", url),
        )


@pytest.mark.parametrize("invalid", [False, True])
def test_tool_call_protocol_and_execution_boundary(monkeypatch, invalid):
    for key, value in {
        "BASE_URL": "https://example.invalid/v1",
        "API_KEY": "test-key-never-real",
        "NAME": "scripted-test-provider",
    }.items():
        monkeypatch.setenv(f"FIELDOPS_MODEL_{key}", value)

    async def exercise():
        store = Store(":memory:")
        app = create_app(store)
        fixture = make_fixture("dimension", 203)
        item = store.create(fixture, "llm")
        session = ToolSession(app, store, item["id"])

        def factory(**kwargs):
            return ScriptedProvider(invalid=invalid, **kwargs)

        if invalid:
            with pytest.raises(ValueError, match="Unknown tool"):
                await llm_plan(session, factory)
        else:
            plan = await llm_plan(session, factory)
            validate_plan(store.get(item["id"]), plan)
            assert store.get(item["id"])["config"] == fixture["config"]
            store.update(item["id"], plan=plan.model_dump(), status="awaiting_approval")
            store.approve(item["id"], digest(plan.model_dump()), 0)
            result = await execute(store, item["id"])
            assert result["verification"]["passed"]
            assert "test-key-never-real" not in json.dumps(result)
        store.close()

    asyncio.run(exercise())
