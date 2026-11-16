// Contract 3.0 (surface study). Types are generated from contract/surface_study.schema.json (`npm run contract`);
// the response is validated at run time against the same schema, so an incompatible file gives an explicit error.
import Ajv2020 from "ajv/dist/2020";
import schema from "../../contract/surface_study.schema.json";
import { semanticViolation } from "./contract";
import type { SurfaceStudy } from "./study.gen";

export type {
  BaselineState, BatchInfo, BoundaryInfo, ChangeWindow, FlagSummary, GcovAcquisition, PolChange, QualityRow, ReferenceState,
  SurfaceStudy, ZoneChange, ZoneConclusion,
} from "./study.gen";

const ajv = new Ajv2020({ allErrors: false, strict: false });
const validate = ajv.compile(schema);
export const STUDY_SCHEMA_VERSION = "3.0";

export function assertSurfaceStudy(data: unknown): asserts data is SurfaceStudy {
  const v = (data as { schema_version?: unknown } | null)?.schema_version;
  if (v !== STUDY_SCHEMA_VERSION) throw new Error(`unsupported schema_version ${String(v)} (expected ${STUDY_SCHEMA_VERSION})`);
  if (!validate(data)) {
    const e = validate.errors?.[0];
    throw new Error(`the study does not satisfy the contract at ${e?.instancePath || "/"}: ${e?.message ?? "invalid"}`);
  }
  const s = semanticViolation(data);
  if (s) throw new Error(`the study does not satisfy the contract at ${s}`);
}
