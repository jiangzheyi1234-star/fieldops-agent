"""Original synthetic cases. Labels never enter the agent's observation surface."""

import random

from .models import Contract, DeploymentConfig

SCENARIOS = {
    "route": ("模型接口路径不兼容", "接入新模型网关后问答返回 404，请检查接口联调。"),
    "credential": ("凭据引用失效", "部署后模型调用失败，请定位，不要在工单中暴露凭据。"),
    "timeout": ("超时预算过短", "服务健康但客户问答偶发超时，需要核查调用预算。"),
    "dimension": ("向量维度不一致", "知识库导入完成，但问答检索报错，请恢复文档查询。"),
    "collection": ("索引配置漂移", "版本升级后检索不到交付手册，检查索引接入。"),
    "worker": ("导入任务未运行", "客户说数据已导入，但是问答一直处于处理中。"),
    "acl": ("租户隔离失效", "请核查新部署的知识助手是否满足租户数据隔离约定。"),
    "stub": ("健康响应掩盖业务失败", "接口返回 200，但客户发现回答没有依据且内容固定。"),
    "compound": ("多处配置漂移", "迁移后问答不可用，修复一处后仍需检查完整交付链路。"),
    "outage": ("上游维护需升级处理", "问答 503，上游维护窗口已开启，需要保留证据并升级处理。"),
    "drift": ("回答内容漂移需人工复核", "配置和健康检查正常，但验收回答不符合客户资料，请保留证据。"),
    "healthy": ("交付验收健康对照", "对当前部署执行验收，确认功能、证据和租户隔离。"),
}


def make_fixture(scenario: str, seed: int) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario")
    rng = random.Random(seed)
    tenant = f"customer-{rng.randint(10, 99)}"
    contract = Contract(
        tenant=tenant,
        collection=f"{tenant}-handbook-v{rng.randint(1, 9)}",
        embedding_dim=rng.choice([192, 384, 768]),
        timeout_ms=2500,
        documents=[
            {
                "id": "SOP-001",
                "tenant": tenant,
                "text": "交付验收要求：接口联调、数据核验、测试报告、客户确认。",
            },
            {
                "id": "SOP-002",
                "tenant": tenant,
                "text": "故障升级流程：记录现象、保留日志、联系负责人、回归验证。",
            },
            {"id": "OTHER-001", "tenant": "foreign-customer", "text": "其他客户的内部合同资料。"},
        ],
    )
    config = DeploymentConfig(
        collection=contract.collection,
        embedding_dim=contract.embedding_dim,
    )
    mutations = {
        "route": {"provider_path": "/chat"},
        "credential": {"credential_ref": "vault://demo/missing"},
        "timeout": {"timeout_ms": rng.choice([100, 300, 500])},
        "dimension": {"embedding_dim": contract.embedding_dim * 2},
        "collection": {"collection": "legacy-empty-index"},
        "worker": {"worker_enabled": False},
        "acl": {"acl_enforced": False},
        "stub": {"answer_mode": "stub"},
        "compound": {
            "provider_path": "/chat",
            "embedding_dim": contract.embedding_dim * 2,
            "worker_enabled": False,
            "acl_enforced": False,
        },
        "outage": {},
        "drift": {},
        "healthy": {},
    }
    config = DeploymentConfig.model_validate(config.model_dump() | mutations[scenario])
    return {
        "title": SCENARIOS[scenario][0],
        "ticket": SCENARIOS[scenario][1],
        "config": config.model_dump(),
        "contract": contract.model_dump(),
        "upstream": {
            "latency_ms": rng.randint(750, 1800),
            "maintenance": scenario == "outage",
            "content_drift": scenario == "drift",
        },
    }
