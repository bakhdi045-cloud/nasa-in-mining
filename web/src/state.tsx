import { createContext, useContext } from "react";
import type { Measurement, MiningCase } from "./contract";

export type ResultKind = "flags" | "coh" | "opt" | "los" | "recurrence" | "none";

export interface TraceTarget {
  label: string;
  display: string;
  measurement?: Measurement;
  pairId?: string;
  layerId?: string;
  note?: string;
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
  openTrace: (t: TraceTarget) => void;
  file: (path: string) => string;
}

export const CaseContext = createContext<CaseState | null>(null);
export function useCase(): CaseState {
  const c = useContext(CaseContext);
  if (!c) throw new Error("CaseContext missing");
  return c;
}
