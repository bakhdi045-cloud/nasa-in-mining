import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within, fireEvent, waitFor } from "@testing-library/react";
import App, { CaseView } from "../App";
import { assertMiningCase, type MiningCase } from "../contract";
import { DICTS, LANGS, makeFmt, translate } from "../i18n";
import { I18nContext, makeI18n } from "../i18nContext";

const recorded = resolve(__dirname, "../../../cases/benguerir/output/case.json");
const realCase = (): MiningCase => JSON.parse(readFileSync(recorded, "utf-8"));

function renderCase(data: MiningCase, lang: "fr" | "en" | "ar" = "fr") {
  return render(<I18nContext.Provider value={makeI18n(lang)}><CaseView data={data} /></I18nContext.Provider>);
}

describe("i18n", () => {
  it("has the same keys in French, English and Arabic", () => {
    const fr = Object.keys(DICTS.fr).sort();
    for (const l of LANGS) expect(Object.keys(DICTS[l]).sort()).toEqual(fr);
  });

  it("translates every key the recorded case refers to", () => {
    const c = realCase();
    const keys = [c.question_key, c.user_key, c.site.description_key, ...c.limits,
      ...c.layers.map((l) => l.title_key), ...c.exports.map((e) => e.description_key),
      ...c.references.flatMap((r) => [r.supports_key, r.cannot_support_key]),
      ...c.validation.flatMap((v) => [...v.evidence_keys, ...v.missing_keys, `level.${v.level}`, `observable.${v.observable}`]),
      ...c.findings.map((f) => `finding.${f.kind}`), ...c.next_checks.map((n) => `next.${n.kind}`),
      ...c.pairs.map((p) => `status.${p.status}`)];
    for (const l of LANGS) for (const k of keys) expect(DICTS[l][k], `${l}:${k}`).toBeDefined();
  });

  it("formats absent numbers as a dash, never as zero", () => {
    const f = makeFmt("fr");
    expect(f.km2(null)).toBe("—");
    expect(f.km2(0)).toMatch(/^0/);
    expect(translate("en", "finding.study_rate_vs_control", { n_above: 3, n_pairs: 4, min_ratio: 1, max_ratio: 2, median_ratio: 1.5 })).toContain("3 of 4");
  });
});

describe("recorded Benguerir case", () => {
  it("satisfies the runtime contract check", () => {
    expect(() => assertMiningCase(realCase())).not.toThrow();
    expect(() => assertMiningCase({ schema_version: "2.0" })).toThrow(/schema_version/);
  });

  it("shows the flagged area of the selected pair exactly as recorded", () => {
    const c = realCase();
    renderCase(c, "en");
    const pairId = c.findings.find((f) => f.kind === "recurrent_cluster")!.params.pair_id as string;
    const pair = c.pairs.find((p) => p.pair_id === pairId)!;
    const area = pair.zones.find((z) => z.zone_id === "study")!.flagged_area_km2.value!;
    const shown = makeFmt("en").km2(area);
    const kpi = document.querySelector(".kpi--lead")!;
    expect(within(kpi as HTMLElement).getByText(shown)).toBeInTheDocument();
  });

  it("traces a value to its pair, granule and files", () => {
    const c = realCase();
    renderCase(c, "en");
    fireEvent.click(document.querySelector(".kpi--lead .value")!);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Where does this value come from?")).toBeInTheDocument();
    expect(within(dialog).getAllByText(/NISAR_L2_PR_GUNW/).length).toBeGreaterThan(0);
    expect(within(dialog).getByText("10.5067/NIL2GUNW-P1")).toBeInTheDocument();
  });

  it("renders an absent measurement as not measured, with its reason", () => {
    const c = realCase();
    const pairId = c.findings.find((f) => f.kind === "recurrent_cluster")!.params.pair_id as string;
    const pair = c.pairs.find((p) => p.pair_id === pairId)!;
    pair.zones[0].flagged_area_km2 = { value: null, unit: "km2", status: "not_measured", reason: "synthetic reason for the test" };
    renderCase(c, "en");
    const kpi = document.querySelector(".kpi--lead") as HTMLElement;
    expect(within(kpi).getByText("not measured")).toBeInTheDocument();
    expect(within(kpi).getByText("synthetic reason for the test")).toBeInTheDocument();
  });

  it("keeps rejected pairs visible as not observed", () => {
    renderCase(realCase(), "fr");
    expect(screen.getAllByText("Écartée par le contrôle qualité").length).toBeGreaterThan(0);
  });

  it("falls back to tables when WebGL is unavailable", () => {
    renderCase(realCase(), "en");
    expect(screen.getByText(/needs WebGL/)).toBeInTheDocument();
  });
});

describe("states without data", () => {
  it("never turns missing data into an absence of change", () => {
    const c = realCase();
    const empty: MiningCase = { ...c, pairs: [], acquisitions: [], layers: [], findings: [], next_checks: [], geometries: [],
      processing: { status: "unavailable", steps: [], blockers: ["blocker.no_radar_products"] }, limits: ["limit.no_data_is_not_no_change"] };
    renderCase(empty, "fr");
    expect(screen.getByText("Aucune observation radar n'est disponible pour ce site")).toBeInTheDocument();
    expect(screen.getByText(/ni « sans changement » ni « sûre »/)).toBeInTheDocument();
  });

  it("explains an API error instead of showing an empty page", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: "case_not_found", message: "no recorded case" }), { status: 404 })));
    render(<App />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText("case_not_found")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
