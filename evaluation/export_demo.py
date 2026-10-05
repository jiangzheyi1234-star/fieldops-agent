"""Export real API workflow recordings for the public, backend-free demo."""

import asyncio
import json
from pathlib import Path

import httpx

from fieldops.api import create_app
from fieldops.fixtures import SCENARIOS
from fieldops.store import Store


async def main():
    store = Store(":memory:")
    app = create_app(store)
    result = {"scope": "real_local_http_sandbox_recordings_not_live_cloud", "recordings": {}}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result["scenarios"] = (await client.get("/api/scenarios")).json()
        result["benchmark"] = (await client.get("/api/benchmark")).json()
        for scenario in SCENARIOS:
            initial = (await client.post("/api/incidents", json={"scenario": scenario, "seed": 201})).json()
            path = f"/api/incidents/{initial['id']}"
            diagnosed = (await client.post(path + "/diagnose")).json()
            approved = diagnosed
            final = diagnosed
            if diagnosed["plan"]["actions"]:
                approval_response = await client.post(
                    path + "/approve", json={"plan_hash": diagnosed["plan_hash"], "revision": 0}
                )
                approved = approval_response.json()
                final = (await client.post(path + "/execute")).json()
            result["recordings"][scenario] = {
                "initial": initial,
                "diagnosed": diagnosed,
                "approved": approved,
                "final": final,
            }
    output = Path(__file__).resolve().parent.parent / "web/public/demo-recordings.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    store.close()
    print(f"Exported {len(result['recordings'])} real workflow recordings")


if __name__ == "__main__":
    asyncio.run(main())
