import argparse
import asyncio
import hashlib
import json
import platform
import statistics
import time
from pathlib import Path

from fieldops.agent import apply_approved, diagnose, execute
from fieldops.api import create_app
from fieldops.fixtures import SCENARIOS, make_fixture
from fieldops.store import Store, digest
from fieldops.verifier import fresh_replay, grade, probe

ROOT = Path(__file__).resolve().parent
METHODS = ("no_op", "one_shot", "without_replay", "fieldops")


def make_cases():
    return [
        {
            "id": f"{scenario}-{seed}",
            "scenario": scenario,
            "seed": seed,
            "split": "dev" if seed < 200 else "test",
            "fixture": make_fixture(scenario, seed),
        }
        for scenario in SCENARIOS
        for seed in [101, 102, 201, 202, 203, 204, 205, 206]
    ]


async def trial(case: dict, method: str) -> dict:
    store = Store(":memory:")
    app = create_app(store, serve_ui=False)
    item = store.create(case["fixture"], "offline")
    started = time.perf_counter()
    try:
        before = grade(item, await probe(app, item))
        if method != "no_op":
            await diagnose(app, store, item["id"], baseline=method == "one_shot")
            item = store.get(item["id"])
            if item["plan"]["actions"]:
                store.approve(item["id"], digest(item["plan"]), item["revision"])
                if method == "without_replay":
                    apply_approved(store, item["id"])
                else:
                    await execute(store, item["id"])
        item = store.get(item["id"])
        if method in ("no_op", "without_replay"):
            # Explicitly modeled unsafe ablation: declare completion from liveness alone.
            declared = (await probe(app, item))["health"]["status"] == 200
            store.update(item["id"], status="verified" if declared else "needs_review")
            item = store.get(item["id"])
        else:
            declared = item["status"] == "verified"
        final = await fresh_replay(item)  # Grader always uses its own pristine environment.
        expected = (
            "escalated"
            if case["scenario"] == "outage"
            else "needs_review"
            if case["scenario"] == "drift"
            else "verified"
        )
        return {
            "case_id": case["id"],
            "method": method,
            "resolved": final["passed"],
            "declared_complete": declared,
            "false_completion": declared and not final["passed"],
            "expected_status": expected,
            "actual_status": item["status"],
            "workflow_correct": item["status"] == expected and declared == final["passed"],
            "initial_checks": before["checks"],
            "final_checks": final["checks"],
            "tool_calls": len(item["evidence"]),
            "config_hash": final["config_hash"],
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "trace": {key: item[key] for key in ("evidence", "plan", "approval", "events")},
        }
    finally:
        store.close()


async def run(split: str, output: Path):
    cases_file = ROOT / "cases.json"
    if not cases_file.exists():
        cases_file.write_text(
            json.dumps(make_cases(), ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    selected = [case for case in cases if case["split"] == split]
    rows = []
    for method in METHODS:
        for case in selected:
            rows.append(await trial(case, method))
    summary = {
        "schema_version": 1,
        "benchmark": "FieldOps synthetic regression v1",
        "mode": "offline_deterministic_not_llm",
        "split": split,
        "cases": len(selected),
        "repairable_cases": sum(case["scenario"] not in ("healthy", "outage", "drift") for case in selected),
        "corpus_sha256": hashlib.sha256(cases_file.read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "methods": {},
    }
    for method in METHODS:
        subset = [row for row in rows if row["method"] == method]
        repairs = [
            row for row in subset if row["case_id"].split("-")[0] not in ("healthy", "outage", "drift")
        ]
        summary["methods"][method] = {
            "resolved": sum(row["resolved"] for row in subset),
            "total": len(subset),
            "resolved_rate": sum(row["resolved"] for row in subset) / len(subset),
            "repair_resolved": sum(row["resolved"] for row in repairs),
            "repair_total": len(repairs),
            "false_completions": sum(row["false_completion"] for row in subset),
            "workflow_correct": sum(row["workflow_correct"] for row in subset),
            "mean_tool_calls": round(statistics.mean(row["tool_calls"] for row in subset), 2),
            "median_elapsed_ms": round(statistics.median(row["elapsed_ms"] for row in subset), 3),
        }
    output.mkdir(parents=True, exist_ok=True)
    (output / "trials.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8", newline="\n"
    )
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    lines = [
        "# FieldOps 合成故障回归测评",
        "",
        f"固定语料 SHA-256：`{summary['corpus_sha256']}`",
        "",
        "确定性离线模式；这是工程回归和评估门禁消融，不是大模型能力成绩或生产故障准确率。",
        f"{split} 集 {len(selected)} 例：{summary['repairable_cases']} 个可修复故障，"
        f"其余 {len(selected) - summary['repairable_cases']} 个为健康对照、上游维护和内容漂移。",
        "",
        "| 方法 | 独立重放成功 | 可修复故障恢复 | 误报完成 | 流程正确 | 平均工具调用 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, m in summary["methods"].items():
        lines.append(
            f"| {name} | {m['resolved']}/{m['total']} | {m['repair_resolved']}/{m['repair_total']} | "
            f"{m['false_completions']} | {m['workflow_correct']}/{m['total']} | {m['mean_tool_calls']} |"
        )
    lines += [
        "",
        "完整逐例检查、诊断证据、审批和操作轨迹保存在 trials.jsonl。",
        "未解决案例：上游维护需要提供方恢复；内容漂移需要人工审阅。二者均不能通过本地配置恢复。",
        "无重放消融复用了同一修复器，只移除完成状态的独立验收门禁；其误报完成表示门禁的必要性。",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), default="test")
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    asyncio.run(run(args.split, args.output))
