import { expect, test } from "@playwright/test";

test("question → data → observation → evidence, in three languages, offline", async ({ page, context }) => {
  // Offline: every request must stay on the local service.
  const external: string[] = [];
  await context.route(/^(?!http:\/\/127\.0\.0\.1:8799).*/, (route) => { external.push(route.request().url()); return route.abort(); });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/");
  await page.getByRole("button", { name: "Français" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Benguerir");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");

  // the displayed flagged area equals the recorded value
  const api = await (await page.request.get("/api/cases")).json();
  const data = await (await page.request.get(`/api/cases/${api[0].case_id}`)).json();
  const pid = data.findings.find((f: { kind: string }) => f.kind === "recurrent_cluster").params.pair_id;
  const area = data.pairs.find((p: { pair_id: string }) => p.pair_id === pid).zones[0].flagged_area_km2.value;
  const shown = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(area);
  await expect(page.locator(".kpi--lead .value__num")).toHaveText(`${shown} km²`);

  // trace a value to its source granule
  await page.locator(".kpi--lead .value").click();
  await expect(page.getByRole("dialog")).toContainText("NISAR_L2_PR_GUNW");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // keyboard: select another pair from the chart
  const point = page.locator(".chart .pt").first();
  await point.focus();
  await page.keyboard.press("Enter");
  await expect(point).toHaveAttribute("aria-pressed", "true");

  // map layer images are served locally
  await expect(page.locator(".map__canvas canvas")).toHaveCount(1);
  const layer = data.layers.find((l: { id: string }) => l.id.startsWith("flags_"));
  expect((await page.request.get(`/api/cases/${data.case_id}/files/${layer.url}`)).ok()).toBeTruthy();

  // Arabic is right-to-left; English renders too
  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("ابن جرير");
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByText("What the data show")).toBeVisible();

  // no horizontal page scroll at this width
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  expect(external.filter((u) => !u.startsWith("data:"))).toEqual([]);
  expect(errors).toEqual([]);
});
