import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const LOCAL = "http://127.0.0.1:8799";

async function offline(page: Page) {
  const external: string[] = [];
  await page.context().route(/^(?!http:\/\/127\.0\.0\.1:8799).*/, (route) => {
    const u = route.request().url();
    if (!u.startsWith("data:") && !u.startsWith("blob:")) external.push(u);
    return route.abort();
  });
  return external;
}

async function study(page: Page) {
  const list = await (await page.request.get(`${LOCAL}/api/studies`)).json();
  return (await page.request.get(`${LOCAL}/api/studies/${list[0].study_id}`)).json();
}

for (const lang of ["fr", "en", "ar"] as const) {
  test(`surface study: five steps, accessibility, no overflow in ${lang}`, async ({ page }) => {
    const external = await offline(page);
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`/?lang=${lang}`);
    await expect(page.locator("html")).toHaveAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    await expect(page.locator(".steps li")).toHaveCount(5);
    await expect(page.locator("#step-conclusion table.conclusions tbody tr").first()).toBeVisible();
    const axe = await new AxeBuilder({ page }).exclude(".maplibregl-canvas").analyze();
    const serious = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(", ")}`)).toEqual([]);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test("surface study: numbers, dependencies and pending states match the recorded run; files are served", async ({ page }) => {
  const external = await offline(page);
  const data = await study(page);
  await page.goto("/?lang=fr");
  // optical support is counted per distinct optical pair
  const strict = data.evidence.optical.find((e: { mode: string }) => e.mode === "strict");
  await expect(page.locator("#step-comparison")).toContainText(`${strict.n_unique_optical_pairs} couple(s) Sentinel-2 distinct(s)`);
  // pending states are visible, nothing is presented as validated
  await expect(page.locator(".badges")).toContainText("Revue humaine en attente");
  await expect(page.locator(".presentation")).toContainText("n'est pas validée");
  await expect(page.locator("#step-comparison")).toContainText("En attente d'annotations");
  // zone conclusions: one row per zone, cause undetermined everywhere
  await expect(page.locator("#step-conclusion table.conclusions tbody tr")).toHaveCount(data.conclusions.length);
  await expect(page.locator("#step-conclusion table.conclusions tbody tr").first()).toContainText("indéterminée");
  // the selected window is shareable through the URL
  const w = data.windows.find((x: { status: string }) => x.status === "computed");
  await page.goto(`/?lang=fr&pair=${w.window_id}&layer=quality`);
  await expect(page.getByRole("combobox").first()).toHaveValue(w.window_id);
  // every layer and export is served locally
  for (const l of data.layers) expect((await page.request.get(`${LOCAL}/api/studies/${data.study_id}/files/${l.url}`)).ok(), l.url).toBeTruthy();
  for (const e of data.exports) expect((await page.request.get(`${LOCAL}/api/studies/${data.study_id}/files/${e.path}`)).ok(), e.path).toBeTruthy();
  await expect(page.locator(".map__canvas canvas")).toHaveCount(1);
  expect(external).toEqual([]);
});

test("surface study: the v2 case stays readable and its optical dependency is stated", async ({ page }) => {
  await offline(page);
  const data = await (await page.request.get(`${LOCAL}/api/cases/${(await (await page.request.get(`${LOCAL}/api/cases`)).json())[0].case_id}`)).json();
  const strict = data.evidence.optical.find((e: { mode: string }) => e.mode === "strict");
  expect([strict.n_radar_comparisons, strict.n_unique_optical_pairs]).toEqual([3, 2]);
  expect(data.evidence.derived_at_read).toBe(true);
  await page.goto("/?lang=en&view=case");
  await expect(page.locator(".kpi--lead .value__num")).toBeVisible();
});

test("surface study: print keeps the map snapshot, limits and sources", async ({ page }) => {
  await offline(page);
  await page.goto("/?lang=en");
  await expect(page.locator(".map__canvas canvas")).toHaveCount(1);
  await page.waitForTimeout(1500);
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".map__print")).toBeVisible();
  await expect(page.locator(".map__print img")).toHaveAttribute("src", /^data:image\/png/);
  await expect(page.locator(".limits").first()).toBeVisible();
  await expect(page.locator(".map__print figcaption")).toContainText("Copernicus");
});
