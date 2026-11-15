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

async function published(page: Page) {
  const list = await (await page.request.get(`${LOCAL}/api/cases`)).json();
  return (await page.request.get(`${LOCAL}/api/cases/${list[0].case_id}`)).json();
}

for (const lang of ["fr", "en", "ar"] as const) {
  test(`accessibility and keyboard in ${lang}`, async ({ page }) => {
    const external = await offline(page);
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`/?lang=${lang}`);
    await expect(page.locator("html")).toHaveAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    await expect(page.locator(".kpi--lead .value__num")).toBeVisible();
    const axe = await new AxeBuilder({ page }).exclude(".maplibregl-canvas").analyze();
    const serious = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(", ")}`)).toEqual([]);

    // keyboard: the skip link comes first, the provenance panel traps focus and gives it back
    await page.keyboard.press("Tab");
    await expect(page.locator(".skip")).toBeFocused();
    const opener = page.locator(".kpi--lead .value");
    await opener.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]"))).toBe(true);
    }
    await expect(page.locator("main")).toHaveAttribute("inert", "");
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(opener).toBeFocused();
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test("values, dates and shareable state match the recorded run, offline", async ({ page }) => {
  const external = await offline(page);
  const data = await published(page);
  const ok = data.pairs.filter((p: { status: string }) => p.status === "ok");
  const target = ok[2];
  await page.goto(`/?lang=fr&pair=${target.pair_id}&layer=coh`);
  const main = target.profiles.find((p: { id: string }) => p.id === data.method.main_profile);
  const v = main.study_flagged_area_km2.value;
  const d = v < 1 ? 3 : 2;
  const shown = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  await expect(page.locator(".kpi--lead .value__num")).toHaveText(`${shown} km²`);
  await expect(page.getByRole("radio", { name: /Cohérence de la paire/ })).toBeChecked();

  // the chart is operable with the keyboard and updates the URL
  const point = page.locator(".chart .pt").first();
  await point.focus();
  await page.keyboard.press("Enter");
  await expect(point).toHaveAttribute("aria-pressed", "true");
  expect(new URL(page.url()).searchParams.get("pair")).not.toBe(target.pair_id);

  // every file referenced by the case is served locally
  for (const l of data.layers) {
    expect((await page.request.get(`${LOCAL}/api/cases/${data.case_id}/files/${l.url}`)).ok(), l.url).toBeTruthy();
  }
  await expect(page.locator(".map__canvas canvas")).toHaveCount(1);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  expect(external).toEqual([]);
});

test("print view keeps a static map with legend, dates and sources", async ({ page }) => {
  await offline(page);
  await page.goto("/?lang=en");
  await expect(page.locator(".map__canvas canvas")).toHaveCount(1);
  await page.waitForTimeout(1500);
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".map__print")).toBeVisible();
  await expect(page.locator(".map__print img")).toHaveAttribute("src", /^data:image\/png/);
  await expect(page.locator(".legend")).toBeVisible();
  await expect(page.locator(".map__print figcaption")).toContainText("Copernicus");
  await expect(page.locator(".limits").first()).toBeVisible();
});
