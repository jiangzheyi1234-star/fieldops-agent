"""Validate a running HTTP deployment, including business workflow and ZIP checks."""

import argparse
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import zipfile


def main(base):
    def request(path, body=None):
        raw = json.dumps(body).encode() if body is not None else None
        with urllib.request.urlopen(
            urllib.request.Request(base + path, data=raw, headers={"Content-Type": "application/json"}),
            timeout=10,
        ) as response:
            return response.read()

    for attempt in range(30):
        try:
            request("/api/meta")
            break
        except (OSError, urllib.error.URLError):
            if attempt == 29:
                raise
            time.sleep(0.5)
    assert b"root" in request("/")
    item = json.loads(request("/api/incidents", {"scenario": "compound", "seed": 201}))
    path = f"/api/incidents/{item['id']}"
    item = json.loads(request(path + "/diagnose", {}))
    assert item["status"] == "awaiting_approval" and len(item["plan"]["actions"]) == 4
    request(path + "/approve", {"plan_hash": item["plan_hash"], "revision": item["revision"]})
    item = json.loads(request(path + "/execute", {}))
    assert item["status"] == "verified" and item["verification"]["passed_count"] == 7
    archive = zipfile.ZipFile(io.BytesIO(request(path + "/bundle")))
    for name, expected in json.loads(archive.read("manifest.json"))["files"].items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == expected
    print("Live HTTP deployment smoke: 4 approved repairs, 7 checks, ZIP hashes passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    main(parser.parse_args().base_url.rstrip("/"))
