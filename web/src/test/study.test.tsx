import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { compile } from "json-schema-to-typescript";
import { DICTS, LANGS } from "../i18n";
import { I18nContext, makeI18n } from "../i18nContext";
import { assertSurfaceStudy, type SurfaceStudy } from "../studyContract";
import { StudyView } from "../study/StudyView";

// the recorded study is the real published pipeline output (vitest runs from web/)
const ROOT = resolve(process.cwd(), "..");
const realStudy = (): SurfaceStudy => JSON.parse(readFileSync(resolve(ROOT, "cases/benguerir-surface-study/output/study.json"), "utf-8"));

beforeEach(() => window.history.replaceState(null, "", "/"));

describe("surface study contract", () => {
  it("generated TypeScript types are in sync with the schema", async () => {
    const schema = JSON.parse(readFileSync(resolve(ROOT, "contract/surface_study.schema.json"), "utf-8"));
    const ts = await compile(schema, "SurfaceStudy", {
      bannerComment: "/* Generated from contract/surface_study.schema.json by `npm run contract`. Do not edit. */",
      additionalProperties: false, unreachableDefinitions: true, style: { printWidth: 120 },
    });
    expect(readFileSync(resolve(process.cwd(), "src/study.gen.ts"), "utf-8")).toBe(ts);
  });

  it("validates the recorded study and rejects altered ones at run time", () => {
    expect(() => assertSurfaceStudy(realStudy())).not.toThrow();
    const bad = realStudy();
    (bad.windows[0].pols[0].zones[0].observed_fraction as { value: number }).value = 1.7;     // a fraction above 1
    expect(() => assertSurfaceStudy(bad)).toThrow(/contract/);
    expect(() => assertSurfaceStudy({ ...realStudy(), schema_version: "2.0" })).toThrow(/schema_version/);
  });
});

describe("surface study texts", () => {
  it("translates every key the recorded study refers to, in French, English and Arabic", () => {
    const s = realStudy();
    const base = (k: string) => k.split(":")[0];
    const keys = [
      s.presentation_level_key, ...s.limits, ...s.layers.map((l) => l.title_key), ...s.exports.map((e) => e.description_key),
      ...s.layers.flatMap((l) => (l.display_note_key ? [l.display_note_key] : [])),
      ...s.layers.flatMap((l) => Object.values(l.legend.class_keys ?? {})),
      ...s.conclusions.flatMap((c) => [c.label_key, ...c.alternative_keys, ...c.to_collect_keys, `s.radar.${c.radar_variation}`, `s.opt.${c.optical_visible_change}`]),
      ...s.batches.flatMap((b) => b.note_keys), ...s.acquisitions.flatMap((a) => [...a.calibration_caveat_keys, ...a.reasons.map((r) => `quality.${r}`)]),
      ...Object.keys(s.boundary.classes).map((k) => `s.class.${k}`), ...Object.values(s.boundary.classes).map((v) => `s.class_state.${v}`),
      ...Object.values(s.boundary.needed_for_next_state).flat(), `s.state.${s.boundary.state}`, `s.review.${s.boundary.review_status}`,
      `s.ref.${s.references.status}`, ...s.references.missing.map((m) => `missing.${m}`), ...Object.keys(s.references.n_units_sampled).map((k) => `s.ref.stratum.${k}`),
      ...s.windows.flatMap((w) => w.pols.map((p) => `s.baseline.${p.baseline.status}`)).map(base),
      ...s.windows.flatMap((w) => [`geometry.${w.direction}`]),
    ];
    for (const l of LANGS) for (const k of keys) expect(DICTS[l][k], `${l}:${k}`).toBeDefined();
  });
});

describe("surface study view", () => {
  const renderStudy = (lang: "fr" | "en" | "ar" = "fr") => render(<I18nContext.Provider value={makeI18n(lang)}><StudyView data={realStudy()} /></I18nContext.Provider>);

  it("shows five steps, the pending states and the optical dependency, and never says validated", () => {
    const s = realStudy();
    const { container } = renderStudy("fr");
    for (const id of ["site", "changes", "quality", "comparison", "conclusion"]) expect(container.querySelector(`#step-${id}`)).not.toBeNull();
    const strict = s.evidence.optical!.find((e) => e.mode === "strict")!;
    expect(within(container.querySelector("#step-comparison") as HTMLElement).getByText(new RegExp(`${strict.n_unique_optical_pairs} couple\\(s\\) Sentinel-2 distinct\\(s\\)`))).toBeInTheDocument();
    expect(screen.getByText("Revue humaine en attente")).toBeInTheDocument();
    expect(screen.getAllByText(/En attente d'annotations/).length).toBeGreaterThan(0);
    expect(container.textContent).not.toMatch(/validée? par|validé indépendamment/i);
  });

  it("gives every zone a row, with an undetermined cause", () => {
    const s = realStudy();
    const { container } = renderStudy("en");
    const rows = container.querySelectorAll("table.conclusions tbody tr");
    expect(rows.length).toBe(s.conclusions.length);
    for (const r of Array.from(rows)) expect(r.textContent).toMatch(/cause undetermined/);
  });

  it("says why a window has no flags instead of showing zero", () => {
    const s = realStudy();
    const w = s.windows.find((x) => x.pols.some((p) => p.pol === "HH" && p.baseline.status === "insufficient_baseline"));
    if (!w) return;                                    // all windows have a reference: nothing to check
    window.history.replaceState(null, "", `/?pair=${w.window_id}`);
    renderStudy("en");
    expect(screen.getAllByText(/insufficient/i).length).toBeGreaterThan(0);
  });

  it("renders in Arabic with the same structure", () => {
    const { container } = renderStudy("ar");
    expect(container.querySelectorAll(".step").length).toBe(5);
  });
});
