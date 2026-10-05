"""An executable, in-process HTTP service fixture; never a production cloud connector."""

from fastapi import APIRouter, HTTPException

from .models import ChatRequest
from .store import Store


def sandbox_router(store: Store) -> APIRouter:
    router = APIRouter(prefix="/sandbox")

    @router.get("/{incident_id}/health")
    def health(incident_id: str):
        store.get(incident_id)
        # Process liveness deliberately does not guarantee end-to-end readiness.
        return {"alive": True, "component": "knowledge-assistant"}

    @router.post("/{incident_id}/chat")
    def chat(incident_id: str, request: ChatRequest):
        item = store.get(incident_id)
        config, contract, upstream = item["config"], item["contract"], item["upstream"]

        def fail(status: int, code: str, detail: str):
            store.event(incident_id, "service_log", {"code": code, "message": detail})
            raise HTTPException(status, {"code": code, "message": detail})

        if upstream["maintenance"]:
            fail(503, "UPSTREAM_MAINTENANCE", "Upstream unavailable; escalate to provider")
        if config["provider_path"] != contract["provider_path"]:
            fail(404, "MODEL_ROUTE_NOT_FOUND", "Configured model gateway route does not exist")
        if config["credential_ref"] != contract["credential_ref"]:
            fail(401, "MODEL_UNAUTHORIZED", "Credential reference cannot be resolved")
        if config["timeout_ms"] < upstream["latency_ms"]:
            fail(
                504,
                "MODEL_TIMEOUT",
                f"Timeout budget {config['timeout_ms']}ms; upstream {upstream['latency_ms']}ms",
            )
        if config["embedding_dim"] != contract["embedding_dim"]:
            fail(400, "VECTOR_DIMENSION_MISMATCH", "Embedding dimension differs from collection schema")
        if config["collection"] != contract["collection"]:
            fail(404, "COLLECTION_NOT_FOUND", "Active collection differs from delivery manifest")
        if not config["worker_enabled"]:
            fail(
                202, "INGESTION_PENDING", "Import worker paused; documents have not reached searchable state"
            )
        if config["answer_mode"] == "stub":
            return {"answer": "Everything is fine", "citations": [], "latency_ms": upstream["latency_ms"]}
        if request.tenant != contract["tenant"] and config["acl_enforced"]:
            return {"answer": "未找到可访问资料", "citations": [], "latency_ms": upstream["latency_ms"]}
        docs = contract["documents"]
        if config["acl_enforced"]:
            docs = [doc for doc in docs if doc["tenant"] == request.tenant]
        selected = docs[1] if "升级" in request.question else docs[0]
        answer = "过期版本的错误验收要求" if upstream.get("content_drift") else selected["text"]
        return {
            "answer": answer,
            "citations": [doc["id"] for doc in docs],
            "latency_ms": upstream["latency_ms"],
        }

    return router
