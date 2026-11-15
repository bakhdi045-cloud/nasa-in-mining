import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { compile } from "json-schema-to-typescript";
import App, { CaseView } from "../App";
import { assertMiningCase, type MiningCase } from "../contract";
import { DICTS, LANGS, makeFmt, translate } from "../i18n";
import { I18nContext, makeI18n } from "../i18nContext";

// vitest runs from web/; the recorded case is the real published pipeline output
const ROOT = resolve(process.cwd(), "..");
const realCase = (): MiningCase => JSON.parse(readFileSync(resolve(ROOT, "cases/benguerir/output/case.json"), "utf-8"));

function renderCase(data: MiningCase, lang: "fr" | "en" | "ar" = "fr") {
  return render(<I18nContext.Provider value={makeI18n(lang)}><CaseView data={data} /></I18nContext.Provider>);
}

beforeEach(() => window.history.replaceState(null, "", "/"));

describe("contract", () => {
  it("generated TypeScript types are in sync with the schema", async () => {
    const schema = JSON.parse(readFileSync(resolve(ROOT, "contract/mining_case.schema.json"), "utf-8"));
    const ts = await compile(schema, "MiningCase", {
      bannerComment: "/* Generated from contract/mining_case.schema.json by `npm run contract`. Do not edit. */",
      additionalProperties: false, unreachableDefinitions: true, style: { printWidth: 120 },
    });
    expect(readFileSync(resolve(process.cwd(), "src/contract.gen.ts"), "utf-8")).toBe(ts);
  });

  it("validates the recorded case and rejects altered ones at run time", () => {
    expect(() => assertMiningCase(realCase())).not.toThrow();
    const bad = realCase();
    (bad.pairs.find((p) => p.status === "ok")!.statistical as { value: number }).value = 1.7;   // a fraction above 1
    expect(() => assertMiningCase(bad)).toThrow(/contract/);
    expect(() => assertMiningCase({ schema_version: "1.0" })).toThrow(/schema_version/);
  });
});

describe("i18n", () => {
  it("has the same keys in French, English and Arabic", () => {
    const fr = Object.keys(DICTS.fr).sort();
    for (const l of LANGS) expect(Object.keys(DICTS[l]).sort()).toEqual(fr);
  });

  it("translates every key the recorded case refers to", () => {
    const c = realCase();
    const base = (k: string) => k.split(":")[0];
    const keys = [c.question_key, c.user_key, c.site.description_key, c.presentation_level_key, c.method.observable_key, ...c.limits,
      ...c.layers.map((l) => l.title_key), ...c.exports.map((e) => e.description_key),
      ...c.references.flatMap((r) => [r.supports_key, r.cannot_support_key]), ...c.method.controls.map((x) => x.label_key),
      ...c.validation.flatMap((v) => [...v.evidence_keys, ...v.missing_keys, ...v.criteria.map(base), `level.${v.level}`, `observable.${v.observable}`]),
      ...c.findings.map((f) => `finding.${f.kind}`), ...c.next_checks.map((n) => `next.${n.kind}`),
      ...c.dossiers.flatMap((d) => [...d.alternative_keys, ...d.to_collect_keys, `zone.${d.zone}`]),
      ...c.pairs.map((p) => `status.${p.status}`), ...(c.processing.blockers ?? []).map(base)];
    for (const l of LANGS) for (const k of keys) expect(DICTS[l][k], `${l}:${k}`).toBeDefined();
  });

  it("states directions from the data, not from the template", () => {
    const p = { direction: "higher", n_lower: 0, n_pairs: 3, median_inner: 0.02, median_outer: 0.01 };
    expect(translate("en", "finding.inner_vs_outer_ring", p)).toContain("higher than");
    expect(translate("en", "finding.inner_vs_outer_ring", { ...p, direction: "mixed" })).toContain("sometimes lower");
    expect(translate("en", "finding.shared_acquisition", { geometry: "g", jaccard_adjacent: 0.2, jaccard_pairs_two_apart: 0.3, elevated: false })).toContain("as much or less");
    expect(translate("fr", "criterion.strict_optical:2/3")).toContain("2 (requis 3)");
  });

  it("formats absent numbers as a dash, never as zero", () => {
    const f = makeFmt("fr");
    expect(f.km2(null)).toBe("—");
    expect(f.km2(0)).toMatch(/^0/);
  });
});

describe("recorded Benguerir case", () => {
  it("shows the main-profile values of the selected pair exactly as recorded, with their interval", () => {
    const c = realCase();
    renderCase(c, "en");
    const pid = c.dossiers[0]?.evidence[0] ?? c.pairs.find((p) => p.status === "ok")!.pair_id;
    const pair = c.pairs.find((p) => p.pair_id === pid)!;
    const main = pair.profiles.find((p) => p.id === c.method.main_profile)!;
    const kpi = document.querySelector(".kpi--lead") as HTMLElement;
    expect(within(kpi).getByText(makeFmt("en").km2(main.study_flagged_area_km2.value))).toBeInTheDocument();
    expect(screen.getAllByText(/95% interval/).length).toBeGreaterThan(0);
  });

  it("traps focus in the provenance panel, makes the page inert, and returns focus to the opener", async () => {
    renderCase(realCase(), "en");
    const opener = document.querySelector(".kpi--lead .value") as HTMLButtonElement;
    opener.focus();
    fireEvent.click(opener);
    const dialog = screen.getByRole("dialog");
    expect(dialog.contains(document.activeElement)).toBe(true);
    expect(document.querySelector("main")!.hasAttribute("inert")).toBe(true);
    expect(within(dialog).getAllByText(/NISAR_L2_PR_GUNW/).length).toBeGreaterThan(0);
    const buttons = dialog.querySelectorAll<HTMLElement>("button, a[href]");
    (buttons[buttons.length - 1]).focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(buttons[0]);
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(document.querySelector(".kpi--lead .value")));
    expect(document.querySelector("main")!.hasAttribute("inert")).toBe(false);
  });

  it("renders an absent measurement as not measured, with its reason", () => {
    const c = realCase();
    const pid = c.dossiers[0]?.evidence[0] ?? c.pairs.find((p) => p.status === "ok")!.pair_id;
    const main = c.pairs.find((p) => p.pair_id === pid)!.profiles.find((p) => p.id === c.method.main_profile)!;
    main.study_flagged_area_km2 = { value: null, unit: "km2", status: "not_measured", reason: "synthetic reason for the test" };
    renderCase(c, "en");
    const kpi = document.querySelector(".kpi--lead") as HTMLElement;
    expect(within(kpi).getByText("not measured")).toBeInTheDocument();
    expect(within(kpi).getByText("synthetic reason for the test")).toBeInTheDocument();
  });

  it("shows the real rejection reasons of the pairs set aside", () => {
    renderCase(realCase(), "en");
    expect(screen.getAllByText(/product mask: secondary acquisition/).length).toBeGreaterThan(0);
  });

  it("keeps the selected pair and layer in the URL", () => {
    const c = realCase();
    const ok = c.pairs.filter((p) => p.status === "ok");
    window.history.replaceState(null, "", `/?pair=${ok[1].pair_id}&layer=coh`);
    renderCase(c, "en");
    expect((screen.getByRole("combobox", { name: /Pair shown/ }) as HTMLSelectElement).value).toBe(ok[1].pair_id);
    act(() => { fireEvent.change(screen.getByRole("combobox", { name: /Pair shown/ }), { target: { value: ok[2].pair_id } }); });
    expect(new URLSearchParams(window.location.search).get("pair")).toBe(ok[2].pair_id);
  });

  it("falls back to tables when WebGL is unavailable", () => {
    renderCase(realCase(), "en");
    expect(screen.getByText(/needs WebGL/)).toBeInTheDocument();
  });
});

describe("states without data", () => {
  it("never turns missing data into an absence of change", () => {
    const c = realCase();
    const empty: MiningCase = { ...c, pairs: [], acquisitions: [], layers: [], findings: [], next_checks: [], geometries: [], dossiers: [],
      processing: { status: "unavailable", rule: "no radar product", steps: [], blockers: ["blocker.no_radar_products"] }, limits: ["limit.no_data_is_not_no_change"] };
    renderCase(empty, "fr");
    expect(screen.getByText("Aucune observation radar n'est disponible pour ce site")).toBeInTheDocument();
    expect(screen.getByText(/ni « sans changement »/)).toBeInTheDocument();
  });

  it("explains an API error instead of showing an empty page", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: "case_not_found", message: "no recorded case" }), { status: 404 })));
    render(<App />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText("case_not_found")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
