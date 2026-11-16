import { createContext, useContext } from "react";
import type { Measurement, MiningCase } from "./contract";

export type ResultKind = "flags" | "coh" | "opt" | "los" | "recurrence" | "observed" | "none";
export const RESULT_KINDS: ResultKind[] = ["flags", "coh", "opt", "los", "recurrence", "observed", "none"];

export interface TraceTarget {
  label: string;
  display: string;
  measurement?: Measurement;
  pairId?: string;
  layerId?: string;
}

export interface CaseState {
  data: MiningCase;
  pairId: string | null;
  setPairId: (id: string) => void;
  result: ResultKind;
  setResult: (k: ResultKind) => void;
  recurrenceGeometry: string | null;
  setRecurrenceGeometry: (g: string) => void;
  focus: [number, number] | null;
  setFocus: (c: [number, number]) => void;
  openTrace: (t: TraceTarget, from: HTMLElement | null) => void;
  file: (path: string) => string;
}

export const CaseContext = createContext<CaseState | null>(null);
export function useCase(): CaseState {
  const c = useContext(CaseContext);
  if (!c) throw new Error("CaseContext missing");
  return c;
}

/** Shareable view state kept in the URL: language, case, run, pair and layer. */
export interface UrlState {
  lang?: string;
  case?: string;
  run?: string;
  pair?: string;
  layer?: string;
  view?: string;
  study?: string;
}

export function readUrl(): UrlState {
  try {
    const q = new URLSearchParams(window.location.search);
    const out: UrlState = {};
    for (const k of ["lang", "case", "run", "pair", "layer", "view", "study"] as const) {
      const v = q.get(k);
      if (v) out[k] = v;
    }
    return out;
  } catch {
    return {};
  }
}

export function writeUrl(patch: UrlState): void {
  try {
    const q = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(patch)) {
      if (v) q.set(k, v);
      else q.delete(k);
    }
    const s = q.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${s ? `?${s}` : ""}${window.location.hash}`);
  } catch {
    /* URL not writable (e.g. sandboxed preview): state stays in memory */
  }
}
