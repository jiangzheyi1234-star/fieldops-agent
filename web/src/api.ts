import type { Benchmark, Incident, Scenario } from "./types";
export const staticDemo = import.meta.env.VITE_STATIC_DEMO === "1";
interface Recording {
  initial: Incident;
  diagnosed: Incident;
  final: Incident;
}
interface Recordings {
  scenarios: Scenario[];
  recordings: Record<string, Recording>;
  benchmark: Benchmark;
}
let loaded: Recordings | undefined;
const sessions = new Map<string, Incident>();
async function recordings() {
  if (!loaded)
    loaded = (await (
      await fetch(`${import.meta.env.BASE_URL}demo-recordings.json`)
    ).json()) as Recordings;
  return loaded;
}
export async function request<T>(path: string, body?: unknown): Promise<T> {
  if (!staticDemo) {
    const response = await fetch(
      `/api${path}`,
      body === undefined
        ? undefined
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
    );
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data === "string" ? data : data.detail || "请求未完成",
      );
    return data as T;
  }
  const demo = await recordings();
  let result: unknown;
  if (path === "/scenarios") result = demo.scenarios;
  else if (path === "/benchmark") result = demo.benchmark;
  else if (path === "/meta") result = { llm_configured: false };
  else if (path === "/incidents" && body === undefined)
    result = [...sessions.values()].reverse();
  else if (path === "/incidents") {
    const scenario = (body as { scenario: string }).scenario;
    const initial = structuredClone(demo.recordings[scenario].initial);
    sessions.set(initial.id, initial);
    result = initial;
  } else {
    const [, , id, action] = path.split("/");
    const record = Object.values(demo.recordings).find(
      (r) => r.initial.id === id,
    );
    const current = sessions.get(id);
    if (!record || !current) throw new Error("请先选择一个演示案例");
    if (action === "diagnose") result = structuredClone(record.diagnosed);
    else if (action === "approve") result = { ...current, status: "approved" };
    else if (action === "execute") result = structuredClone(record.final);
    else result = current;
    sessions.set(id, result as Incident);
  }
  return result as T;
}
