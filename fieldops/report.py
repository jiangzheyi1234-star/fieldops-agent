import io
import json
import zipfile

from .store import digest


def delivery_bundle(item: dict) -> bytes:
    verification = item["verification"]
    lines = [
        f"# {item['title']} 交付报告",
        "",
        f"工单：{item['id']}",
        f"状态：{item['status']}",
        f"模式：{item['mode']}（offline 为确定性诊断，非大模型成绩）",
        "",
        "## 客户现象",
        item["ticket"],
        "",
        "## 诊断与变更",
        (item["plan"] or {}).get("summary", "尚未完成诊断"),
    ]
    for action in (item["plan"] or {}).get("actions", []):
        lines.append(
            f"- {action['field']} → {action['value']}；依据 {', '.join(action['evidence_ids'])} / {action['runbook_id']}"
        )
    lines += ["", "## 独立验证", "新数据库和服务应用重放配置；不接受健康检查或方案文本替代业务结果。"]
    if verification:
        lines += [
            f"- {'PASS' if c['passed'] else 'FAIL'} {c['id']}：{c['detail']}" for c in verification["checks"]
        ]
    else:
        lines.append("尚无验证结果，不能声明交付成功。")
    lines += [
        "",
        "## 客户操作与验收",
        "1. 对照 deployment.json 检查配置变更及审批。",
        "2. 重放交付验收和故障升级问题，检查引用。",
        "3. 用未授权租户核验访问控制。",
        "4. 根据 verification.json 和 events.json 审阅失败项；全部通过后确认验收。",
        "",
        "## 范围",
        "仅为合成数据和本地 HTTP 沙箱；没有连接真实客户、云平台或设备。",
    ]
    files = {
        "report.md": "\n".join(lines).encode(),
        "deployment.json": json.dumps(item["config"], ensure_ascii=False, indent=2).encode(),
        "contract.json": json.dumps(item["contract"], ensure_ascii=False, indent=2).encode(),
        "evidence.json": json.dumps(item["evidence"], ensure_ascii=False, indent=2).encode(),
        "events.json": json.dumps(item["events"], ensure_ascii=False, indent=2).encode(),
        "verification.json": json.dumps(verification, ensure_ascii=False, indent=2).encode(),
    }
    import hashlib

    manifest = {
        "schema_version": 1,
        "incident_id": item["id"],
        "config_hash": digest(item["config"]),
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    files["manifest.json"] = json.dumps(manifest, indent=2).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()
