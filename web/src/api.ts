import { assertMiningCase, type ApiErrorBody, type MiningCase } from "./contract";

export class LoadError extends Error {
  constructor(public code: string, message: string) {
    super(message);
  }
}

async function getJson(url: string): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new LoadError("service_unreachable", `no answer from ${url}`);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body as ApiErrorBody | null;
    throw new LoadError(err?.error ?? `http_${res.status}`, err?.message ?? `HTTP ${res.status} on ${url}`);
  }
  return body;
}

export const API = "/api";

export interface CaseListItem {
  case_id: string;
  published_run: string | null;
  runs: string[];
  error?: string;
  message?: string;
}

export function fileUrl(caseId: string, path: string, run?: string | null): string {
  const p = path.split("/").map(encodeURIComponent).join("/");
  return `${API}/cases/${encodeURIComponent(caseId)}/files/${p}${run ? `?run=${encodeURIComponent(run)}` : ""}`;
}

export async function listCases(): Promise<CaseListItem[]> {
  const list = (await getJson(`${API}/cases`)) as CaseListItem[];
  if (!Array.isArray(list) || list.length === 0) throw new LoadError("no_case", "the service holds no recorded case");
  return list;
}

export async function loadCase(caseId?: string, run?: string): Promise<{ data: MiningCase; list: CaseListItem[] }> {
  const list = await listCases();
  const item = list.find((c) => c.case_id === caseId) ?? list.find((c) => !c.error) ?? list[0];
  if (item.error) throw new LoadError(item.error, item.message ?? "the recorded case is unreadable");
  const r = run && item.runs.includes(run) ? run : undefined;
  const data = await getJson(`${API}/cases/${encodeURIComponent(item.case_id)}${r ? `?run=${encodeURIComponent(r)}` : ""}`);
  try {
    assertMiningCase(data);
  } catch (e) {
    throw new LoadError("contract_violation", (e as Error).message);
  }
  return { data, list };
}
