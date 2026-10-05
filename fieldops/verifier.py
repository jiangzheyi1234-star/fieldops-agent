"""Independent end-state grader. A plan or a green health probe is never sufficient."""

import httpx


async def probe(app, item: dict) -> dict:
    path = f"/sandbox/{item['id']}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://sandbox") as client:
        health = await client.get(path + "/health")
        responses = {}
        for name, tenant, question in [
            ("acceptance", item["contract"]["tenant"], "交付验收要求是什么？"),
            ("escalation", item["contract"]["tenant"], "故障升级流程是什么？"),
            ("foreign", "unauthorized-tenant", "交付验收要求是什么？"),
        ]:
            response = await client.post(path + "/chat", json={"tenant": tenant, "question": question})
            responses[name] = {"status": response.status_code, "body": response.json()}
    return {"health": {"status": health.status_code, "body": health.json()}, "responses": responses}


def grade(item: dict, observation: dict) -> dict:
    contract = item["contract"]
    first, second = contract["documents"][:2]
    owned_ids = {doc["id"] for doc in contract["documents"] if doc["tenant"] == contract["tenant"]}
    a, b, foreign = (observation["responses"][name] for name in ("acceptance", "escalation", "foreign"))

    def citations_ok(response, required):
        values = response["body"].get("citations", [])
        return bool(values) and required in values and set(values) <= owned_ids

    config = item["config"]
    checks = [
        {
            "id": "liveness",
            "layer": "readiness",
            "passed": observation["health"]["status"] == 200,
            "detail": "HTTP /health 返回 200；仅代表进程存活",
        },
        {
            "id": "acceptance_answer",
            "layer": "behavior",
            "passed": a["status"] == 200 and a["body"].get("answer") == first["text"],
            "detail": "验收问题回答与客户资料一致",
        },
        {
            "id": "escalation_answer",
            "layer": "behavior",
            "passed": b["status"] == 200 and b["body"].get("answer") == second["text"],
            "detail": "升级问题回答与客户资料一致",
        },
        {
            "id": "acceptance_citations",
            "layer": "evidence",
            "passed": citations_ok(a, first["id"]),
            "detail": "验收回答引用属于当前客户且包含 SOP-001",
        },
        {
            "id": "escalation_citations",
            "layer": "evidence",
            "passed": citations_ok(b, second["id"]),
            "detail": "升级回答引用属于当前客户且包含 SOP-002",
        },
        {
            "id": "tenant_isolation",
            "layer": "conformance",
            "passed": foreign["status"] == 200
            and foreign["body"].get("citations") == []
            and foreign["body"].get("answer") == "未找到可访问资料",
            "detail": "未授权租户不得得到客户资料或引用",
        },
        {
            "id": "manifest_conformance",
            "layer": "conformance",
            "passed": all(
                config[key] == contract[key]
                for key in ("provider_path", "credential_ref", "embedding_dim", "collection")
            )
            and config["timeout_ms"] >= item["upstream"]["latency_ms"]
            and config["worker_enabled"]
            and config["acl_enforced"]
            and config["answer_mode"] == "grounded",
            "detail": "配置满足交付清单、处理预算与访问控制约定",
        },
    ]
    return {
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "passed_count": sum(check["passed"] for check in checks),
        "total": len(checks),
    }


async def fresh_replay(item: dict) -> dict:
    # Imports here avoid an API factory cycle. New DB + new app discard old runtime/log state.
    from .api import create_app
    from .store import Store, digest

    replay_store = Store(":memory:")
    replay = replay_store.create(
        {key: item[key] for key in ("title", "ticket", "config", "contract", "upstream")}, "offline"
    )
    app = create_app(store=replay_store, serve_ui=False)
    try:
        observation = await probe(app, replay)
        result = grade(replay, observation)
        return result | {
            "fresh_replay": True,
            "config_hash": digest(item["config"]),
            "contract_hash": digest(item["contract"]),
            "observations": observation,
        }
    finally:
        replay_store.close()
