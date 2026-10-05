"""Original runbooks + BM25 retrieval with evidence identifiers."""

import math
import re
from collections import Counter

RUNBOOKS = [
    {
        "id": "RB-ROUTE",
        "field": "provider_path",
        "code": "MODEL_ROUTE_NOT_FOUND",
        "title": "模型接口联调",
        "text": "MODEL_ROUTE_NOT_FOUND route 404 网关 路径 provider_path。检查网关兼容的路径与交付清单。只更新已确认的接口路径，重新执行问答和引用核验。",
    },
    {
        "id": "RB-AUTH",
        "field": "credential_ref",
        "code": "MODEL_UNAUTHORIZED",
        "title": "凭据引用核验",
        "text": "MODEL_UNAUTHORIZED auth 401 credential_ref 凭据。使用交付清单中的凭据引用，禁止输出密钥。恢复引用后检查模型接口。",
    },
    {
        "id": "RB-TIMEOUT",
        "field": "timeout_ms",
        "code": "MODEL_TIMEOUT",
        "title": "调用预算调整",
        "text": "MODEL_TIMEOUT timeout 504 timeout_ms 超时。检查上游耗时与调用预算。使用批准的预算，避免无限重试。回归两个业务问题。",
    },
    {
        "id": "RB-DIM",
        "field": "embedding_dim",
        "code": "VECTOR_DIMENSION_MISMATCH",
        "title": "向量 schema 一致性",
        "text": "VECTOR_DIMENSION_MISMATCH embedding_dim dimension 向量 维度。对照交付清单和索引 schema，恢复指定维度，不随意删除或重建客户索引。",
    },
    {
        "id": "RB-INDEX",
        "field": "collection",
        "code": "COLLECTION_NOT_FOUND",
        "title": "索引配置核验",
        "text": "COLLECTION_NOT_FOUND collection index 索引 漂移。核查活动 collection 与交付清单，修正索引引用后验证文档 ID 和回答内容。",
    },
    {
        "id": "RB-WORKER",
        "field": "worker_enabled",
        "code": "INGESTION_PENDING",
        "title": "导入链路排障",
        "text": "INGESTION_PENDING worker_enabled worker 导入。检查 worker 是否暂停，批准后开启导入任务，核验资料真正可检索。",
    },
    {
        "id": "RB-ACL",
        "field": "acl_enforced",
        "code": "TENANT_LEAK",
        "title": "租户访问控制",
        "text": "TENANT_LEAK acl_enforced tenant ACL 租户 隔离。强制租户过滤。用客户与未授权租户分别探测，确认未授权请求没有引用或内部内容。",
    },
    {
        "id": "RB-ANSWER",
        "field": "answer_mode",
        "code": "UNGROUNDED_ANSWER",
        "title": "业务回答验收",
        "text": "UNGROUNDED_ANSWER answer_mode stub 回答 引用。健康检查 200 不能替代业务验收，启用 grounded 模式并检查两类问题的回答和引用。",
    },
    {
        "id": "RB-ESCALATE",
        "field": None,
        "code": "UPSTREAM_MAINTENANCE",
        "title": "外部依赖升级处理",
        "text": "UPSTREAM_MAINTENANCE 503 维护 upstream 不可用。无法通过本地配置修复。保留证据、升级给提供方；禁止声明已恢复或进行无依据修改。",
    },
]


def tokens(text: str) -> list[str]:
    ascii_words = re.findall(r"[a-z0-9_]+", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    return ascii_words + ["".join(chinese[i : i + 2]) for i in range(len(chinese) - 1)]


class RunbookIndex:
    def __init__(self):
        self.counts = [Counter(tokens(book["text"])) for book in RUNBOOKS]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average = sum(self.lengths) / len(self.lengths)

    def search(self, query: str, limit: int = 3) -> list[dict]:
        scores = []
        for book, count, length in zip(RUNBOOKS, self.counts, self.lengths, strict=True):
            score = 0.0
            for token in set(tokens(query)):
                freq = count[token]
                df = sum(token in c for c in self.counts)
                idf = math.log(1 + (len(RUNBOOKS) - df + 0.5) / (df + 0.5))
                score += idf * freq * 2.2 / (freq + 1.2 * (0.25 + 0.75 * length / self.average))
            if score > 0:
                scores.append(book | {"score": round(score, 5)})
        return sorted(scores, key=lambda book: (-book["score"], book["id"]))[:limit]
