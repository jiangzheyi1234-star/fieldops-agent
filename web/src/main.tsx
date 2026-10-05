import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { request, staticDemo } from "./api";
import type { Benchmark, Incident, Scenario } from "./types";
import "./style.css";

const labels: Record<string, string> = {
  created: "待诊断",
  diagnosing: "诊断中",
  awaiting_approval: "待审批",
  approved: "已批准",
  executing: "执行中",
  verified: "验收通过",
  escalated: "已升级处理",
  needs_review: "待人工复核",
  diagnosis_failed: "诊断未完成",
  verification_failed: "验证未完成",
};
const fields: Record<string, string> = {
  provider_path: "模型接口路径",
  credential_ref: "凭据引用",
  timeout_ms: "超时预算",
  embedding_dim: "向量维度",
  collection: "知识库索引",
  worker_enabled: "导入任务",
  acl_enforced: "租户隔离",
  answer_mode: "回答模式",
};
const toolNames: Record<string, string> = {
  read_config: "配置与交付约定",
  probe_service: "HTTP 业务探测",
  search_runbooks: "操作手册检索",
};
const eventNames: Record<string, string> = {
  tool_result: "收集诊断证据",
  service_log: "服务运行日志",
  plan_submitted: "提交修复方案",
  human_approval: "人工审批确认",
  config_applied: "应用配置更新",
  fresh_replay: "独立重放验证",
  model_usage: "模型调用记录",
};
const methodNames: Record<string, string> = {
  no_op: "仅看健康检查",
  one_shot: "单次错误匹配",
  without_replay: "移除验收门禁",
  fieldops: "FieldOps 完整流程",
};
function Badge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{labels[status] || status}</span>;
}
function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]),
    [selected, setSelected] = useState("compound");
  const [incidents, setIncidents] = useState<Incident[]>([]),
    [active, setActive] = useState<Incident | null>(null);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null),
    [tab, setTab] = useState("work");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [llm, setLlm] = useState(false),
    [mode, setMode] = useState("offline");
  useEffect(() => {
    Promise.all([
      request<Scenario[]>("/scenarios"),
      request<Incident[]>("/incidents"),
      request<Benchmark>("/benchmark"),
      request<{ llm_configured: boolean }>("/meta"),
    ])
      .then(([s, i, b, m]) => {
        setScenarios(s);
        setIncidents(i);
        setActive(i[0] || null);
        setBenchmark(b);
        setLlm(m.llm_configured);
      })
      .catch((e) => setError(String(e.message)));
  }, []);
  async function action(path: string, body: unknown = {}) {
    setBusy(true);
    setError("");
    try {
      const item = await request<Incident>(path, body);
      setActive(item);
      setIncidents(await request<Incident[]>("/incidents"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作未完成");
    } finally {
      setBusy(false);
    }
  }
  async function create() {
    setTab("work");
    await action("/incidents", { scenario: selected, mode, seed: 201 });
  }
  function downloadRecording() {
    if (!active) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(active, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `fieldops-${active.id}-recording.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  const metric = benchmark?.methods?.fieldops;
  const markers = active
    ? [
        "✓",
        active.evidence.length >= 2 ? "✓" : "2",
        active.plan?.actions.length
          ? active.events.some((e) => e.kind === "human_approval")
            ? "✓"
            : "3"
          : active.plan
            ? "—"
            : "3",
        active.events.some((e) => e.kind === "config_applied")
          ? "✓"
          : active.plan && !active.plan.actions.length
            ? "—"
            : "4",
        active.verification ? (active.verification.passed ? "✓" : "!") : "5",
      ]
    : [];
  return (
    <div className="app-shell">
      <aside className="rail">
        <a className="brand" href="#">
          <span className="brand-icon">
            F<span>↗</span>
          </span>
          <b>
            FieldOps<small>AI DELIVERY WORKSPACE</small>
          </b>
        </a>
        <div className="workspace">
          <span className="avatar">D</span>
          <div>
            交付工程实验室<small>个人作品 · FDE</small>
          </div>
          <span className="online" />
        </div>
        <div className="rail-label">工作空间</div>
        <button
          className={tab === "work" ? "nav active" : "nav"}
          onClick={() => setTab("work")}
        >
          <span>▦</span>交付工作台
          <span className="nav-count">{incidents.length}</span>
        </button>
        <button
          className={tab === "evidence" ? "nav active" : "nav"}
          onClick={() => setTab("evidence")}
        >
          <span>◎</span>验收与证据
        </button>
        <button
          className={tab === "eval" ? "nav active" : "nav"}
          onClick={() => setTab("eval")}
        >
          <span>▥</span>测评报告
        </button>
        <div className="rail-label history-label">最近工单</div>
        <div className="history">
          {incidents.slice(0, 8).map((i) => (
            <button
              key={i.id}
              disabled={busy}
              className={
                active?.id === i.id ? "history-item current" : "history-item"
              }
              onClick={() => {
                setActive(i);
                setTab("work");
              }}
            >
              <span className={`dot ${i.status}`} />
              <div>
                {i.title}
                <small>
                  #{i.id.slice(0, 8)} · {labels[i.status]}
                </small>
              </div>
            </button>
          ))}
        </div>
        <div className="rail-footer">
          <div className="small-title">可追溯的每一次交付</div>
          <p>
            从客户现象到业务验证，
            <br />
            让证据贯穿问题处理流程。
          </p>
          <a
            href="https://github.com/jiangzheyi1234-star/fieldops-agent"
            target="_blank"
            rel="noreferrer"
          >
            查看源码与研究依据 ↗
          </a>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            工作空间 <span>/</span>{" "}
            <b>
              {tab === "eval"
                ? "测评报告"
                : tab === "evidence"
                  ? "验收与证据"
                  : "交付工作台"}
            </b>
          </div>
          <div className="top-meta">
            <span className="online" />{" "}
            {staticDemo ? "真实记录回放" : "本地 HTTP 沙箱"}
            <span className="version">v0.1</span>
          </div>
        </header>
        <div className="mobile-nav">
          <button onClick={() => setTab("work")}>交付工作台</button>
          <button onClick={() => setTab("evidence")}>验收与证据</button>
          <button onClick={() => setTab("eval")}>测评报告</button>
        </div>
        <div className="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">FORWARD DEPLOYED ENGINEERING</div>
              <h1>
                {tab === "eval"
                  ? "让结果经得起复测"
                  : tab === "evidence"
                    ? "每个结论，都有证据"
                    : "把 AI 应用交付到可用"}
              </h1>
              <p>配置联调、故障定位、人工审批与独立验收，在一个工作台完成。</p>
            </div>
            <div className="scope-label">
              <span>◈</span> 合成客户数据
              <br />
              <small>
                {staticDemo
                  ? "离线交互回放 · 无后端执行"
                  : "确定性诊断 / 可选 LLM 工具调用"}
              </small>
            </div>
          </div>
          {staticDemo && (
            <div className="demo-note">
              演示说明：页面回放本地 HTTP
              沙箱真实执行的记录。按钮用于查看流程，公开页面不会调用模型或修改部署。
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <div className="metrics">
            <div>
              <span>可修复故障恢复</span>
              <strong>
                {metric
                  ? `${metric.repair_resolved} / ${metric.repair_total}`
                  : "—"}
              </strong>
              <small>合成测试集 · 独立重放</small>
            </div>
            <div>
              <span>业务验收成功</span>
              <strong>
                {metric ? `${metric.resolved} / ${metric.total}` : "—"}
              </strong>
              <small>保留 12 个未恢复案例</small>
            </div>
            <div>
              <span>误报完成</span>
              <strong className="green">
                {metric?.false_completions ?? "—"} <em>例</em>
              </strong>
              <small>业务失败不得声明完成</small>
            </div>
            <div>
              <span>验收检查维度</span>
              <strong>
                7 <em>项</em>
              </strong>
              <small>业务 · 引用 · 隔离 · 配置</small>
            </div>
          </div>
          {tab === "eval" ? (
            <section className="panel evaluation">
              <div className="panel-head">
                <div>
                  <h2>固定案例，比较完整结果</h2>
                  <p>
                    72 个测试案例 / 24 个开发案例 ·
                    确定性工程回归，非大模型能力成绩
                  </p>
                </div>
                <span className="pill">OFFLINE / v1</span>
              </div>
              <div className="chart">
                {benchmark &&
                  Object.entries(benchmark.methods).map(([name, m]) => (
                    <div className="chart-row" key={name}>
                      <span>{methodNames[name]}</span>
                      <div className="bar-track">
                        <div
                          className={name === "fieldops" ? "bar full" : "bar"}
                          style={{ width: `${(m.resolved / m.total) * 100}%` }}
                        />
                      </div>
                      <b>
                        {m.resolved}/{m.total}
                      </b>
                      <small>{m.false_completions} 次误报</small>
                    </div>
                  ))}
              </div>
              <div className="eval-explain">
                <h3>为什么保留失败案例？</h3>
                <p>
                  上游维护无法通过本地配置恢复，应升级处理；回答内容漂移需要人工复核。两类案例共
                  12 例，正确处理不等于业务已经恢复。
                </p>
                <p>
                  单次错误匹配只修复首个显式错误，完整流程还检查配置漂移、固定回答与租户泄漏。移除验收门禁后，12
                  个失败案例会被误报完成。
                </p>
              </div>
              <div className="hash">
                语料 SHA-256 <code>{benchmark?.corpus_sha256}</code>
              </div>
              <a
                className="text-link"
                href="https://github.com/jiangzheyi1234-star/fieldops-agent/tree/main/evaluation"
                target="_blank"
                rel="noreferrer"
              >
                查看逐例结果、评估协议和复现命令 ↗
              </a>
            </section>
          ) : (
            <>
              <section className="panel start-panel">
                <div className="panel-head">
                  <div>
                    <h2>开始一个交付案例</h2>
                    <p>选择客户现象，检查运行证据，再确认修复。</p>
                  </div>
                  <span className="pill">12 个场景</span>
                </div>
                <div className="start-controls">
                  <label>
                    故障场景
                    <select
                      value={selected}
                      onChange={(e) => setSelected(e.target.value)}
                    >
                      {scenarios.map((s) => (
                        <option value={s.id} key={s.id}>
                          {s.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    诊断模式
                    <select
                      value={mode}
                      onChange={(e) => setMode(e.target.value)}
                    >
                      <option value="offline">离线确定性诊断</option>
                      <option value="llm" disabled={!llm || staticDemo}>
                        LLM 工具调用{!llm ? "（未配置）" : ""}
                      </option>
                    </select>
                  </label>
                  <button
                    className="primary"
                    disabled={busy || !scenarios.length}
                    onClick={create}
                  >
                    ＋ 新建工单
                  </button>
                </div>
              </section>
              {!active ? (
                <div className="empty">
                  <span>↗</span>
                  <h2>交付从一个真实现象开始</h2>
                  <p>
                    试试“多处配置漂移”，观察健康检查通过后，业务探测如何发现问题。
                  </p>
                </div>
              ) : (
                <>
                  <section className="panel incident-header">
                    <div>
                      <div className="incident-number">工单 #{active.id}</div>
                      <h2>{active.title}</h2>
                      <p>{active.ticket}</p>
                    </div>
                    <Badge status={active.status} />
                    <div className="steps">
                      {[
                        "客户现象",
                        "证据诊断",
                        "方案审批",
                        "执行更新",
                        "独立验收",
                      ].map((name, i) => (
                        <React.Fragment key={name}>
                          <div
                            className={
                              markers[i] === "✓" ? "step reached" : "step"
                            }
                          >
                            <span>{markers[i]}</span>
                            {name}
                          </div>
                          {i < 4 && (
                            <div
                              className={
                                markers[i] === "✓"
                                  ? "step-line reached"
                                  : "step-line"
                              }
                            />
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </section>
                  <div className="detail-grid">
                    <section className="panel plan-panel">
                      <div className="panel-head">
                        <div>
                          <h2>
                            {tab === "evidence"
                              ? "验收检查结果"
                              : "诊断与修复方案"}
                          </h2>
                          <p>
                            {active.mode === "llm"
                              ? "模型调用只生成待审批方案"
                              : "离线模式根据配置、探测与手册形成方案"}
                          </p>
                        </div>
                        <span className="panel-icon">◈</span>
                      </div>
                      {tab === "evidence" ? (
                        <VerificationView incident={active} />
                      ) : (
                        <>
                          <div className="plan-summary">
                            {active.plan?.summary ||
                              "等待收集配置快照与 HTTP 业务探测结果。诊断不会修改当前部署。"}
                          </div>
                          {active.plan?.actions.map((a, i) => (
                            <div className="repair" key={a.field}>
                              <div className="repair-index">{i + 1}</div>
                              <div className="repair-main">
                                <div>
                                  <b>{fields[a.field] || a.field}</b>
                                  <span className="runbook">
                                    {a.runbook_id}
                                  </span>
                                </div>
                                <div className="diff">
                                  <code>
                                    {String(active.initial_config[a.field])}
                                  </code>
                                  <span>→</span>
                                  <code className="new-value">
                                    {String(a.value)}
                                  </code>
                                </div>
                                <p>{a.reason}</p>
                                <div className="citations">
                                  {a.evidence_ids.map((id) => (
                                    <span key={id}>{id}</span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ))}
                          {active.plan?.unresolved.map((u) => (
                            <div className="review-note" key={u}>
                              ↗ {u}
                            </div>
                          ))}
                          <div className="action-bar">
                            {active.status === "created" && (
                              <button
                                className="primary"
                                disabled={busy}
                                onClick={() =>
                                  action(`/incidents/${active.id}/diagnose`)
                                }
                              >
                                {busy ? "正在收集证据…" : "运行诊断 →"}
                              </button>
                            )}
                            {active.status === "awaiting_approval" && (
                              <>
                                <button
                                  className="primary"
                                  disabled={busy}
                                  onClick={() =>
                                    action(`/incidents/${active.id}/approve`, {
                                      plan_hash: active.plan_hash,
                                      revision: active.revision,
                                    })
                                  }
                                >
                                  确认方案并批准
                                </button>
                                <small>仅授权以上配置变更</small>
                              </>
                            )}
                            {active.status === "approved" && (
                              <button
                                className="primary"
                                disabled={busy}
                                onClick={() =>
                                  action(`/incidents/${active.id}/execute`)
                                }
                              >
                                {busy
                                  ? "正在重放验证…"
                                  : "执行修复与独立验证 →"}
                              </button>
                            )}
                            {active.verification && (
                              <button
                                className="secondary"
                                onClick={() => setTab("evidence")}
                              >
                                查看验收证据 →
                              </button>
                            )}
                          </div>
                          {active.verification && (
                            <div
                              className={
                                active.verification.passed
                                  ? "verification-banner"
                                  : "verification-banner warning"
                              }
                            >
                              <b>
                                {active.verification.passed
                                  ? "✓ 独立验收通过"
                                  : "! 业务尚未全部恢复"}
                              </b>
                              <span>
                                {active.verification.passed_count}/
                                {active.verification.total} 项通过 ·
                                新建服务沙箱重放
                              </span>
                            </div>
                          )}
                        </>
                      )}
                    </section>
                    <aside className="panel evidence-panel">
                      <div className="panel-head">
                        <div>
                          <h2>证据与执行记录</h2>
                          <p>
                            {active.evidence.length} 条工具证据 · 可追溯操作轨迹
                          </p>
                        </div>
                        <span className="panel-icon">◎</span>
                      </div>
                      <div className="evidence-list">
                        {active.evidence.map((e) => (
                          <details key={e.id}>
                            <summary>
                              <span className="evidence-id">{e.id}</span>
                              <b>{toolNames[e.tool]}</b>
                              <span>＋</span>
                            </summary>
                            <pre>{JSON.stringify(e.data, null, 2)}</pre>
                          </details>
                        ))}
                        {!active.evidence.length && (
                          <p className="muted">
                            运行诊断后，配置、探测和手册证据会出现在这里。
                          </p>
                        )}
                      </div>
                      <div className="timeline">
                        {active.events
                          .filter((e) => e.kind !== "service_log")
                          .slice(-6)
                          .map((e) => (
                            <div key={e.sequence}>
                              <span />
                              <p>
                                {eventNames[e.kind] || e.kind}
                                <small>
                                  {new Date(e.at).toLocaleTimeString("zh-CN", {
                                    hour12: false,
                                  })}{" "}
                                  · #{e.sequence}
                                </small>
                              </p>
                            </div>
                          ))}
                      </div>
                      {active.plan && (
                        <div className="export">
                          <b>交付材料已留存</b>
                          <p>
                            {staticDemo
                              ? "下载本案例的证据与验证记录。"
                              : "配置、证据、操作轨迹、验收报告与 SHA-256 清单。"}
                          </p>
                          {staticDemo ? (
                            <button
                              className="secondary"
                              onClick={downloadRecording}
                            >
                              ↓ 下载演示记录
                            </button>
                          ) : (
                            <a
                              className="secondary"
                              href={`/api/incidents/${active.id}/bundle`}
                            >
                              ↓ 导出交付包 ZIP
                            </a>
                          )}
                        </div>
                      )}
                    </aside>
                  </div>
                </>
              )}
            </>
          )}
          <footer>
            FieldOps · 原创工程作品{" "}
            <span>数据与案例均为合成 · LLM 实测成绩尚未提供</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
function VerificationView({ incident }: { incident: Incident }) {
  const v = incident.verification;
  if (!v)
    return (
      <div className="plan-summary">
        方案执行后，在新建沙箱中进行独立验收。当前还没有验证结论。
      </div>
    );
  return (
    <>
      <div
        className={
          v.passed ? "verification-banner" : "verification-banner warning"
        }
      >
        <b>{v.passed ? "✓ 全部检查通过" : "! 保留失败证据"}</b>
        <span>
          {v.passed_count} / {v.total}
        </span>
      </div>
      <div className="checks">
        {v.checks.map((c) => (
          <div key={c.id}>
            <span className={c.passed ? "check pass" : "check fail"}>
              {c.passed ? "✓" : "×"}
            </span>
            <div>
              <b>{c.detail}</b>
              <small>
                {c.layer} / {c.id}
              </small>
            </div>
          </div>
        ))}
      </div>
      <div className="hash">
        重放配置 SHA-256 <code>{v.config_hash}</code>
      </div>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
