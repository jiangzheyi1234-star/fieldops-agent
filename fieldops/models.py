from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeploymentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_path: str = "/v1/chat/completions"
    credential_ref: str = "vault://demo/model"
    timeout_ms: int = Field(default=2500, ge=50, le=5000)
    embedding_dim: int = Field(default=384, ge=1, le=4096)
    collection: str = "acme-handbook"
    worker_enabled: bool = True
    acl_enforced: bool = True
    answer_mode: Literal["grounded", "stub"] = "grounded"


class Contract(BaseModel):
    tenant: str = "acme"
    provider_path: str = "/v1/chat/completions"
    credential_ref: str = "vault://demo/model"
    embedding_dim: int = 384
    collection: str = "acme-handbook"
    timeout_ms: int = 2500
    documents: list[dict] = Field(default_factory=list)


class CreateIncident(BaseModel):
    scenario: str = "dimension"
    seed: int = Field(default=101, ge=0, le=999999)
    mode: Literal["offline", "llm"] = "offline"
    ticket: str | None = Field(default=None, max_length=3000)


class ChatRequest(BaseModel):
    tenant: str
    question: str = Field(min_length=1, max_length=500)


PatchField = Literal[
    "provider_path",
    "credential_ref",
    "timeout_ms",
    "embedding_dim",
    "collection",
    "worker_enabled",
    "acl_enforced",
    "answer_mode",
]


class RepairAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: PatchField
    value: str | int | bool
    reason: str = Field(min_length=1, max_length=500)
    evidence_ids: list[str] = Field(min_length=1, max_length=10)
    runbook_id: str


class RepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=1500)
    actions: list[RepairAction] = Field(max_length=8)
    unresolved: list[str] = Field(default_factory=list, max_length=10)


class Approval(BaseModel):
    plan_hash: str = Field(min_length=64, max_length=64)
    revision: int = Field(ge=0)
