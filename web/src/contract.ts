// Contract 2.0. Types are generated from contract/mining_case.schema.json (`npm run contract`); responses are
// validated at run time against the same schema with ajv, so an incompatible file gives an explicit error.
import Ajv2020 from "ajv/dist/2020";
import schema from "../../contract/mining_case.schema.json";
import type { MiningCase } from "./contract.gen";

export type {
  Acquisition, Cluster, ControlDef, CrossGeometry, Dossier, Finding, GeometrySummary, Layer, Legend, LosPair,
  Measurement, MiningCase, NextCheck, OpticalComparison, OpticalScene, PairResult, PerimeterVersion, Profile,
  Recurrence1 as Recurrence, Reference, Uncertainty, ValidationItem, WindowMatch, Zone, ZoneMetrics,
} from "./contract.gen";

export type Params = Record<string, unknown>;

export interface ApiErrorBody {
  error: string;
  message: string;
}

const ajv = new Ajv2020({ allErrors: false, strict: false });
const validate = ajv.compile(schema);

export const SCHEMA_VERSION = "2.1";
export const READABLE_VERSIONS = ["2.0", "2.1"];   // 2.1 only adds optional evidence blocks

/** Rules the JSON schema cannot express, mirrored from the Pydantic validators. Returns the first violation. */
export function semanticViolation(node: unknown, path = ""): string | null {
  if (typeof node === "number" && !Number.isFinite(node)) return `${path}: non-finite number`;
  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) {
      const v = semanticViolation(node[i], `${path}/${i}`);
      if (v) return v;
    }
    return null;
  }
  if (node && typeof node === "object") {
    const o = node as Record<string, unknown>;
    if ("status" in o && "unit" in o && "value" in o) {                  // a Measurement
      const { value, unit, status, reason, uncertainty } = o as { value: number | null; unit: string; status: string; reason?: string; uncertainty?: unknown };
      if (status === "measured" && value == null) return `${path}: measured value is null`;
      if (status !== "measured" && (value != null || uncertainty != null)) return `${path}: unmeasured value carries a number`;
      if (value == null && !reason) return `${path}: absent value without reason`;
      if (unit === "fraction" && value != null && (value < 0 || value > 1)) return `${path}: fraction outside [0, 1]`;
    }
    if (o.kind === "block_bootstrap_interval" && typeof o.low === "number" && typeof o.high === "number" && o.low > o.high) {
      return `${path}: interval with low > high`;
    }
    for (const [k, v] of Object.entries(o)) {
      const r = semanticViolation(v, `${path}/${k}`);
      if (r) return r;
    }
  }
  return null;
}

export function assertMiningCase(data: unknown): asserts data is MiningCase {
  const v = (data as { schema_version?: unknown } | null)?.schema_version;
  if (typeof v !== "string" || !READABLE_VERSIONS.includes(v)) throw new Error(`unsupported schema_version ${String(v)} (expected ${READABLE_VERSIONS.join(" or ")})`);
  if (!validate(data)) {
    const e = validate.errors?.[0];
    throw new Error(`the case does not satisfy the contract at ${e?.instancePath || "/"}: ${e?.message ?? "invalid"}`);
  }
  const s = semanticViolation(data);
  if (s) throw new Error(`the case does not satisfy the contract at ${s}`);
}
