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

export function fileUrl(caseId: string, path: string): string {
  return `${API}/cases/${encodeURIComponent(caseId)}/files/${path.split("/").map(encodeURIComponent).join("/")}`;
}

export async function loadCase(caseId?: string): Promise<MiningCase> {
  let id = caseId;
  if (!id) {
    const list = (await getJson(`${API}/cases`)) as { case_id: string; error?: string; message?: string }[];
    if (!Array.isArray(list) || list.length === 0) throw new LoadError("no_case", "the service holds no recorded case");
    const usable = list.find((c) => !c.error);
    if (!usable) throw new LoadError(list[0].error ?? "case_error", list[0].message ?? "the recorded case is unreadable");
    id = usable.case_id;
  }
  const data = await getJson(`${API}/cases/${encodeURIComponent(id)}`);
  try {
    assertMiningCase(data);
  } catch (e) {
    throw new LoadError("contract_violation", (e as Error).message);
  }
  return data;
}
