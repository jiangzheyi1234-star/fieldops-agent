export type Json =
  null | boolean | number | string | Json[] | { [key: string]: Json };
export interface Evidence {
  id: string;
  tool: string;
  arguments: Record<string, Json>;
  data: Record<string, Json>;
}
export interface Action {
  field: string;
  value: Json;
  reason: string;
  evidence_ids: string[];
  runbook_id: string;
}
export interface Plan {
  summary: string;
  actions: Action[];
  unresolved: string[];
}
export interface Verification {
  passed: boolean;
  passed_count: number;
  total: number;
  fresh_replay: boolean;
  config_hash: string;
  checks: { id: string; layer: string; passed: boolean; detail: string }[];
}
export interface Incident {
  id: string;
  title: string;
  ticket: string;
  status: string;
  mode: string;
  revision: number;
  config: Record<string, Json>;
  initial_config: Record<string, Json>;
  contract: Record<string, Json>;
  created_at: string;
  evidence: Evidence[];
  plan: Plan | null;
  plan_hash: string | null;
  verification: Verification | null;
  events: { sequence: number; kind: string; at: string; hash: string }[];
}
export interface Scenario {
  id: string;
  title: string;
  ticket: string;
}
export interface Metric {
  resolved: number;
  total: number;
  repair_resolved: number;
  repair_total: number;
  false_completions: number;
  workflow_correct: number;
  mean_tool_calls: number;
}
export interface Benchmark {
  cases: number;
  mode: string;
  corpus_sha256: string;
  methods: Record<string, Metric>;
}
