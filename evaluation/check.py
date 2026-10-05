import json
from pathlib import Path

ROOT = Path(__file__).parent
EXPECTED = {
    "no_op": (6, 0, 66),
    "one_shot": (42, 36, 0),
    "without_replay": (60, 54, 12),
    "fieldops": (60, 54, 0),
}


def main():
    import hashlib

    summary = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line) for line in (ROOT / "results/trials.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert summary["corpus_sha256"] == hashlib.sha256((ROOT / "cases.json").read_bytes()).hexdigest()
    assert summary["cases"] == 72 and len(rows) == 288
    for name, expected in EXPECTED.items():
        metrics = summary["methods"][name]
        assert (metrics["resolved"], metrics["repair_resolved"], metrics["false_completions"]) == expected
        selected = [row for row in rows if row["method"] == name]
        assert len({row["case_id"] for row in selected}) == 72
        assert all(
            row["resolved"] == all(check["passed"] for check in row["final_checks"]) for row in selected
        )
        assert metrics["resolved"] == sum(row["resolved"] for row in selected)
        assert metrics["false_completions"] == sum(
            row["declared_complete"] and not row["resolved"] for row in selected
        )
    assert summary["methods"]["fieldops"]["workflow_correct"] == 72
    print("Fixed-corpus regression and per-case grading consistency passed")


if __name__ == "__main__":
    main()
