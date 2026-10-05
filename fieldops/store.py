import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.commit()

    def create(self, fixture: dict, mode: str) -> dict:
        item = fixture | {
            "id": uuid.uuid4().hex[:12],
            "mode": mode,
            "status": "created",
            "revision": 0,
            "events": [],
            "evidence": [],
            "plan": None,
            "verification": None,
            "approval": None,
            "initial_config": fixture["config"].copy(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.put(item)
        return item

    def get(self, incident_id: str) -> dict:
        with self.lock:
            row = self.db.execute("SELECT payload FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if not row:
            raise KeyError(incident_id)
        return json.loads(row[0])

    def list(self) -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT payload FROM incidents ORDER BY rowid DESC LIMIT 100").fetchall()
        return [json.loads(row[0]) for row in rows]

    def put(self, item: dict):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO incidents VALUES (?, ?)", (item["id"], canonical(item)))

    def event(self, incident_id: str, kind: str, content: dict) -> dict:
        with self.lock:
            item = self.get(incident_id)
            previous = item["events"][-1]["hash"] if item["events"] else "0" * 64
            event = {
                "sequence": len(item["events"]) + 1,
                "kind": kind,
                "content": content,
                "at": datetime.now(UTC).isoformat(),
                "previous_hash": previous,
            }
            event["hash"] = digest(event)
            item["events"].append(event)
            self.put(item)
            return event

    def update(self, incident_id: str, **changes) -> dict:
        with self.lock:
            item = self.get(incident_id)
            item.update(changes)
            self.put(item)
            return item

    def approve(self, incident_id: str, plan_hash: str, revision: int) -> dict:
        with self.lock:
            item = self.get(incident_id)
            if item["status"] != "awaiting_approval" or item["revision"] != revision:
                raise Conflict("状态或版本已变化，请重新获取当前方案")
            if not item["plan"] or digest(item["plan"]) != plan_hash:
                raise Conflict("审批方案摘要不匹配")
            item.update(status="approved", approval={"plan_hash": plan_hash, "revision": revision})
            self.put(item)
            self.event(incident_id, "human_approval", item["approval"])
            return self.get(incident_id)

    def close(self):
        self.db.close()
