"""Opt-in live model evaluation. Never called by the offline benchmark or CI."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from fieldops.agent import diagnose, execute
from fieldops.api import create_app
from fieldops.store import Conflict, Store, digest
from fieldops.verifier import fresh_replay


async def main(limit, output):
    cases = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))
    selected = sorted([case for case in cases if case["split"] == "test"], key=lambda case: case["seed"])[
        :limit
    ]
    rows = []
    for case in selected:
        store = Store(":memory:")
        app = create_app(store)
        item = store.create(case["fixture"], "llm")
        error = None
        try:
            item = await diagnose(app, store, item["id"])
            if item["plan"]["actions"]:
                store.approve(item["id"], digest(item["plan"]), 0)
                item = await execute(store, item["id"])
        except (ValueError, KeyError, httpx.HTTPError, Conflict) as exc:
            error = type(exc).__name__  # No credential-bearing HTTP error strings.
            item = store.get(item["id"])
        grade = await fresh_replay(item)
        rows.append(
            {
                "case_id": case["id"],
                "status": item["status"],
                "error_type": error,
                "passed": grade["passed"],
                "checks": grade["checks"],
                "model": os.getenv("FIELDOPS_MODEL_NAME"),
                "tool_calls": len(item["evidence"]),
                "usage": [event["content"] for event in item["events"] if event["kind"] == "model_usage"],
            }
        )
        store.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"mode": "live_llm", "cases": len(rows), "results": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Recorded {len(rows)} live trials at {output}; provider usage may incur charges.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Explicit opt-in: may incur model API charges.")
    parser.add_argument("--max-cases", type=int, choices=range(1, 73), default=2)
    parser.add_argument("--output", type=Path, default=Path("data/live-llm-results.json"))
    args = parser.parse_args()
    asyncio.run(main(args.max_cases, args.output))
