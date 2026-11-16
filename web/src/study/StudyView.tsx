import { useCallback, useMemo, useState } from "react";
import { studyFileUrl } from "../api";
import { formatMeasurement, intervalText } from "../components/Value";
import { useI18n } from "../i18nContext";
import { readUrl, writeUrl } from "../state";
import type { ChangeWindow, SurfaceStudy } from "../studyContract";
import { StudyMap } from "./StudyMap";

export const STUDY_STEPS = ["site", "changes", "quality", "comparison", "conclusion"] as const;
type Step = (typeof STUDY_STEPS)[number];
type LayerKind = "delta" | "flags" | "quality" | "optical" | "none";
type Meas = Parameters<typeof formatMeasurement>[0];

function Section({ id, n, children }: { id: Step; n: number; children: React.ReactNode }) {
  const { t } = useI18n();
  return (
    <section id={`step-${id}`} className={`step step--${id}`} aria-labelledby={`h-${id}`}>
      <h2 id={`h-${id}`} className="step__title"><span className="step__n" aria-hidden="true">{n}</span>{t(`sstep.${id}`)}</h2>
      {children}
    </section>
  );
}

function Num({ m, kind = "num" }: { m: Meas; kind?: Parameters<typeof formatMeasurement>[1] }) {
  const { t, f } = useI18n();
  const ci = intervalText(m, kind, f);
  return <>{formatMeasurement(m, kind, f, t)}{ci ? <span className="muted small"> {ci}</span> : null}</>;
}

const hh = (w: ChangeWindow) => w.pols.find((p) => p.pol === "HH");

function windowLabel(w: ChangeWindow, f: ReturnType<typeof useI18n>["f"]) {
  return `${f.date(w.before_date)} → ${f.date(w.after_date)}`;
}

function DiffChart({ windows }: { windows: ChangeWindow[] }) {
  const { t, f } = useI18n();
  const rows = windows.filter((w) => w.span_days === 12 && w.status === "computed" && hh(w)?.study_minus_control_db.value != null)
    .sort((a, b) => a.before_date.localeCompare(b.before_date));
  if (!rows.length) return null;
  const vals = rows.map((w) => hh(w)!.study_minus_control_db.value as number);
  const lim = Math.max(0.5, ...vals.map((v) => Math.abs(v))) * 1.15;
  const W = 640, H = 150, bw = Math.min(26, (W - 40) / rows.length - 4), mid = H / 2;
  return (
    <figure className="chart">
      <figcaption>{t("s.diff.chart")}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("s.diff.chart")} className="chart__svg">
        <line x1="30" x2={W} y1={mid} y2={mid} stroke="currentColor" strokeOpacity="0.4" />
        {rows.map((w, i) => {
          const v = vals[i];
          const x = 36 + i * ((W - 40) / rows.length);
          const h = (Math.abs(v) / lim) * (mid - 8);
          return (
            <g key={w.window_id}>
              <rect x={x} y={v >= 0 ? mid - h : mid} width={bw} height={Math.max(h, 1)} className={w.direction === "ascending" ? "bar bar--asc" : "bar bar--desc"}>
                <title>{`${windowLabel(w, f)} · ${t(`geometry.${w.direction}`)} · ${f.num(v, 2)} dB`}</title>
              </rect>
            </g>
          );
        })}
        <text x="2" y="12" className="chart__tick">+{f.num(lim, 1)}</text>
        <text x="2" y={H - 4} className="chart__tick">−{f.num(lim, 1)}</text>
      </svg>
    </figure>
  );
}

export function StudyView({ data, run }: { data: SurfaceStudy; run?: string }) {
  const { t, f } = useI18n();
  const url = readUrl();
  const file = useCallback((p: string) => studyFileUrl(data.study_id, p, run), [data.study_id, run]);
  const computed = data.windows.filter((w) => w.status === "computed");
  const pilot = data.windows.find((w) => w.development_window && w.after_date === "2026-08-28" && w.status === "computed");
  const [wid, setWid] = useState<string>(
    (url.pair && data.windows.some((w) => w.window_id === url.pair) ? url.pair : pilot?.window_id ?? computed[0]?.window_id ?? data.windows[0]?.window_id) ?? "");
  const [kind, setKind] = useState<LayerKind>((["delta", "flags", "quality", "optical", "none"] as string[]).includes(url.layer ?? "") ? (url.layer as LayerKind) : "delta");
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const [zoneOpen, setZoneOpen] = useState<string | null>(null);
  const w = data.windows.find((x) => x.window_id === wid) ?? data.windows[0];
  const p = w ? hh(w) : undefined;
  const layerFor = useCallback((k: LayerKind) => {
    if (!w || k === "none") return undefined;
    const id = k === "delta" ? `delta_HH_${w.window_id}` : k === "flags" ? `flags_HH_${w.window_id}` : k === "quality" ? `quality_${w.window_id}` : `opt_${w.window_id}`;
    return data.layers.find((l) => l.id === id);
  }, [w, data.layers]);
  const shown = layerFor(kind);
  const optPair = w?.optical.find((c) => c.status === "ok" && c.mode === "strict") ?? w?.optical.find((c) => c.status === "ok");
  const base = optPair ? data.layers.find((l) => l.id === `s2rgb_${optPair.after_item}`) : undefined;
  const select = (id: string) => { setWid(id); writeUrl({ pair: id }); };
  const pick = (k: LayerKind) => { setKind(k); writeUrl({ layer: k }); };
  const vUrl = data.exports.find((e) => e.id === "verification_zones")?.path;
  const kinds: { k: LayerKind; label: string; ok: boolean }[] = [
    { k: "delta", label: t("s.layer.delta"), ok: !!layerFor("delta") }, { k: "flags", label: t("s.layer.flags"), ok: !!layerFor("flags") },
    { k: "quality", label: t("s.layer.quality"), ok: !!layerFor("quality") }, { k: "optical", label: t("s.layer.optical"), ok: !!layerFor("optical") },
    { k: "none", label: t("s.layer.none"), ok: true }];
  const b = data.boundary;
  const lc = (b.automated_checks as { landcover_2021_share?: { inside?: Record<string, number>; outside_band_300m?: Record<string, number> } }).landcover_2021_share;
  const proto = data.protocol.parameters as Record<string, number>;
  const groupsOf = (mode: string) => data.evidence.optical?.find((e) => e.mode === mode);
  const report = data.exports.find((e) => e.id === "report_html");
  const windowRows = useMemo(() => [...data.windows].sort((a, b2) => a.direction.localeCompare(b2.direction) || a.before_date.localeCompare(b2.before_date)), [data.windows]);
  const qrows = data.quality.filter((q) => q.window_id === w?.window_id && q.pol === "HH");
  const reasonKeys = Object.keys(qrows[0]?.reasons ?? {});

  return (
    <main id="main" className="layout">
      <Section id="site" n={1}>
        <p className="lede">{t("s.site.lede")}</p>
        <dl className="facts">
          <dt>{t("s.site.state")}</dt>
          <dd><span className={`tag tag--${b.state}`}>{t(`s.state.${b.state}`)}</span> <span className="tag tag--pending">{t(`s.review.${b.review_status}`)}</span></dd>
          <dt>{t("s.site.source")}</dt><dd>{b.source} · {f.date(b.source_date)} · {b.license}</dd>
          <dt>{t("s.site.area")}</dt><dd>{f.km2(b.area_km2)}</dd>
          <dt>{t("s.site.legal")}</dt><dd>{t("s.site.legal.text")}</dd>
        </dl>
        <h3>{t("s.site.classes")}</h3>
        <ul className="classes">{Object.entries(b.classes).map(([k, v]) => <li key={k}><b>{t(`s.class.${k}`)}</b> — {t(`s.class_state.${v}`)}</li>)}</ul>
        <h3>{t("s.site.zones")}</h3>
        <ul className="versions">
          {data.zones.filter((z) => z.role !== "exclusion").map((z) => <li key={z.id}><b>{t(`zone.${z.id === "study" ? "study" : z.id === "control" ? "ring_inner" : "panels"}`)}</b> — {f.km2(z.area_km2)} · {z.source}{z.source_date ? ` · ${f.date(z.source_date)}` : ""}</li>)}
        </ul>
        <p className="muted small">{t("s.site.control_note")}</p>
        {lc?.inside ? (
          <details>
            <summary>{t("s.site.checks")}</summary>
            <p className="small">{t("s.site.landcover")}</p>
            <ul className="versions">
              {Object.keys({ ...lc.inside, ...(lc.outside_band_300m ?? {}) }).map((k) => <li key={k}>{k}: {f.pct(lc.inside?.[k] ?? 0, 0)} / {f.pct(lc.outside_band_300m?.[k] ?? 0, 0)}</li>)}
            </ul>
          </details>
        ) : null}
        <h3>{t("s.site.next")}</h3>
        <ul className="versions">{Object.values(b.needed_for_next_state).flat().map((k) => <li key={k}>{t(k)}</li>)}</ul>
      </Section>

      <aside className="layout__map"><div className="layout__sticky">
        <StudyMap centroid={data.site.centroid as [number, number]} zonesUrl={data.zones_url} verificationUrl={vUrl} base={base} result={shown} focus={focus} file={file}
          resultLabel={shown ? t(shown.title_key) : t("map.none")} />
      </div></aside>

      <Section id="changes" n={2}>
        <p className="lede">{t("s.changes.lede")}</p>
        <label className="picker">
          <span>{t("s.changes.choose")}</span>
          <select value={wid} onChange={(e) => select(e.target.value)}>
            {["ascending", "descending"].map((d) => (
              <optgroup key={d} label={t(`geometry.${d}`)}>
                {windowRows.filter((x) => x.direction === d).map((x) => (
                  <option key={x.window_id} value={x.window_id}>{windowLabel(x, f)} ({x.span_days} d){x.status === "rejected" ? ` — ${t("s.window.rejected")}` : ""}{x.development_window ? ` · ${t("s.col.dev")}` : ""}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <fieldset className="map__group">
          <legend>{t("s.layer.choose")}</legend>
          {kinds.map((o) => (
            <label key={o.k} className={o.ok ? "radio" : "radio radio--off"}>
              <input type="radio" name="slayer" value={o.k} checked={kind === o.k} disabled={!o.ok} onChange={() => pick(o.k)} /><span>{o.label}</span>
            </label>
          ))}
        </fieldset>
        {w?.status === "rejected" ? <p className="notice">{t("s.window.rejected_reason", { r: w.reasons.join("; ") })}</p> : null}
        {p && w?.status === "computed" ? (
          <>
            <p className="small muted">{w.batch_id} · {w.geometry_id} · {t(`geometry.${w.direction}`)}{w.development_window ? ` · ${t("s.dev.title")}` : ""}</p>
            {p.baseline.status === "ok" && p.flags ? (
              <>
                <p>{t("s.flags.explain", { k: p.baseline.k_sigma ?? null, sigma: p.baseline.sigma_db?.value ?? null, centre: p.baseline.centre_db?.value ?? null,
                  ctrl: p.flags.control_fraction.value, study: p.flags.study_fraction.value })}</p>
                <p>{t("s.flags.areas", { area: p.flags.study_flagged_area_km2.value, dark: p.flags.darker_area_km2.value, bright: p.flags.brighter_area_km2.value })}</p>
                <p className="small muted">{t("s.flags.sensitivity")} : {Object.entries(p.flags.ratio_block_sensitivity).map(([bm, v]) => `${bm} m ${v ? `[${f.num(v[0], 2)} – ${f.num(v[1], 2)}]` : "—"}`).join(" · ")}</p>
              </>
            ) : <p className="notice">{t("s.baseline.insufficient_baseline")} — {t("s.baseline.n_detail", { n: p.baseline.n_pairs, need: proto.min_disjoint_pairs })}</p>}
            {w.pols.some((x) => x.pol === "HV") ? <p className="small muted">{t("s.hv.note")}</p> : null}
          </>
        ) : null}
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t("s.table")}>
          <table className="pairs">
            <caption className="sr-only">{t("sstep.changes")}</caption>
            <thead><tr><th scope="col">{t("s.col.window")}</th><th scope="col">{t("s.col.orbit")}</th><th scope="col">{t("s.col.span")}</th><th scope="col">{t("s.col.study")}</th><th scope="col">{t("s.col.diff")}</th>
              <th scope="col">{t("s.col.baseline")}</th><th scope="col">{t("s.col.ratio")}</th><th scope="col"><abbr title={t("s.dev.title")}>{t("s.col.dev")}</abbr></th></tr></thead>
            <tbody>
              {windowRows.map((x) => {
                const px = hh(x);
                const st = px?.zones.find((z) => z.zone_id === "study");
                return (
                  <tr key={x.window_id} className={x.window_id === wid ? "is-sel" : undefined}>
                    <td><button type="button" className="link" aria-pressed={x.window_id === wid} onClick={() => select(x.window_id)}>{windowLabel(x, f)}</button>{x.status === "rejected" ? <> <span className="tag tag--rejected">{t("s.window.rejected")}</span></> : null}</td>
                    <td>{t(`geometry.${x.direction}`)}</td><td>{x.span_days} d</td>
                    <td>{st ? <Num m={st.aggregate_db as Meas} /> : "—"}</td><td>{px ? <Num m={px.study_minus_control_db as Meas} /> : "—"}</td>
                    <td>{px ? (px.baseline.status === "ok" ? t("s.baseline.ok", { n: px.baseline.n_pairs }) : t(`s.baseline.${px.baseline.status}`)) : "—"}</td>
                    <td>{px?.flags ? <Num m={px.flags.ratio as Meas} kind="ratio" /> : "—"}</td><td>{x.development_window ? "•" : ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <DiffChart windows={data.windows} />
      </Section>

      <Section id="quality" n={3}>
        <p className="lede">{t("s.quality.lede")}</p>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t("s.table")}>
          <table>
            <caption className="sr-only">{t("sstep.quality")}</caption>
            <thead><tr><th scope="col">{t("s.q.batch")}</th><th scope="col">{t("s.q.crid")}</th><th scope="col">{t("s.q.usable")}</th><th scope="col">{t("s.q.rejected")}</th><th scope="col">{t("s.q.gaps")}</th></tr></thead>
            <tbody>
              {data.batches.map((bt) => {
                const rej = data.acquisitions.filter((a) => a.status === "rejected" && a.geometry_id === bt.geometry_id && a.crid === bt.crid);
                return (
                  <tr key={bt.batch_id}>
                    <td>{t(`geometry.${bt.direction}`)} · {bt.geometry_id}<br /><span className="small muted">{bt.note_keys.map((k) => t(k)).join(" · ")}</span></td>
                    <td>{bt.collection}<br />{bt.crid}</td><td>{bt.n_usable}/{bt.n_acquisitions}</td>
                    <td>{rej.length ? rej.map((a) => `${f.date(a.time_utc)} (${a.reasons.map((r) => t(`quality.${r}`)).join(", ")})`).join("; ") : t("s.q.none")}</td>
                    <td>{bt.gaps.length ? bt.gaps.map((g) => <div key={String(g.between)}>{f.date(String((g.between as string[])[0]))} → {f.date(String((g.between as string[])[1]))} ({String(g.span_days)} d) — {g.documented_instrument_gap ? t("s.q.gap_documented") : t("s.q.gap_other")}</div>) : t("s.q.none")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {w ? (
          <>
            <h3>{t("s.q.window")} — {windowLabel(w, f)}</h3>
            <div className="table-wrap" tabIndex={0} role="region" aria-label={t("s.table")}>
              <table>
                <thead><tr><th scope="col">{t("s.q.zone")}</th><th scope="col">{t("s.q.observed")}</th>{reasonKeys.filter((k) => qrows.some((q) => (q.reasons[k].value ?? 0) > 0)).map((k) => <th key={k} scope="col">{t(`quality.${k}`)}</th>)}</tr></thead>
                <tbody>
                  {qrows.map((q) => (
                    <tr key={q.zone_id}><th scope="row">{t(q.zone_id === "study" ? "zone.study" : "s.site.zones")}{q.zone_id === "control" ? " (1–4 km)" : ""}</th><td><Num m={q.observed_fraction as Meas} kind="pct" /></td>
                      {reasonKeys.filter((k) => qrows.some((r) => (r.reasons[k].value ?? 0) > 0)).map((k) => <td key={k}><Num m={q.reasons[k] as Meas} kind="pct" /></td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
        <details>
          <summary>{t("s.q.caveats")}</summary>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={t("s.table")}><table>
            <thead><tr><th scope="col">{t("s.col.window")}</th><th scope="col">{t("s.q.look")}</th><th scope="col">{t("s.q.looks")}</th><th scope="col">{t("s.q.incidence")}</th><th scope="col">{t("s.q.caveats")}</th></tr></thead>
            <tbody>{data.acquisitions.map((a) => (
              <tr key={a.acquisition_id}><td>{a.acquisition_id}</td><td>{Object.entries(a.noise_floor_db).map(([k, m]) => `${k} ${formatMeasurement(m as Meas, "num1", f, t)} dB`).join(" · ")}</td>
                <td><Num m={a.median_looks as Meas} kind="num1" /></td><td><Num m={a.median_incidence_deg as Meas} kind="num1" />°</td><td className="small">{a.calibration_caveat_keys.map((k) => t(k)).join(" · ")}</td></tr>))}</tbody>
          </table></div>
        </details>
      </Section>

      <Section id="comparison" n={4}>
        <p className="lede">{t("s.cmp.lede")}</p>
        {(["strict", "exploratory"] as const).map((mode) => {
          const e = groupsOf(mode);
          if (!e) return null;
          return (
            <div key={mode}>
              <p><b>{t("s.cmp.optical", { mode, n_radar: e.n_radar_comparisons, n_pairs: e.n_unique_optical_pairs, n_ci: e.n_groups_ci_above_1 })}</b></p>
              {e.groups.length ? (
                <div className="table-wrap" tabIndex={0} role="region" aria-label={t("s.table")}><table>
                  <thead><tr><th scope="col">{t("s.cmp.group")}</th><th scope="col">{t("s.cmp.before")}</th><th scope="col">{t("s.cmp.after")}</th><th scope="col">{t("s.cmp.windows")}</th><th scope="col">{t("s.cmp.ci")}</th></tr></thead>
                  <tbody>{e.groups.map((g) => <tr key={g.group_id}><td>{g.group_id}</td><td>{f.date(g.before_datetime)}</td><td>{f.date(g.after_datetime)}</td><td className="small">{g.pair_ids.map((id) => id.replace(/^GCOV_/, "").replace(/_P0\d+$/, "")).join(", ")}</td><td>{g.n_ci_above_1}</td></tr>)}</tbody>
                </table></div>
              ) : null}
            </div>
          );
        })}
        <p className="notice">{t("s.cmp.dependency")}</p>
        {w ? (
          <>
            <h3>{t("s.cmp.window")} — {windowLabel(w, f)}</h3>
            {w.optical.length ? (
              <ul className="versions">{w.optical.map((c) => <li key={c.mode}>{c.status === "ok"
                ? t("s.cmp.row", { mode: c.mode, b: c.before_datetime, a: c.after_datetime, pr: c.p_optical_given_radar.value, pn: c.p_optical_given_not_radar.value, ratio: c.association_ratio.value,
                    lo: c.association_ratio.uncertainty?.low ?? null, hi: c.association_ratio.uncertainty?.high ?? null, j: c.jaccard.value })
                : t("s.cmp.row_absent", { mode: c.mode, status: c.reason ?? c.status })}</li>)}</ul>
            ) : <p className="muted">{t("s.cmp.none")}</p>}
            {w.gunw_context ? <p className="small muted">{t("s.cmp.gunw", { ratio: (w.gunw_context.ratio as number) ?? null, lo: (w.gunw_context.ci_low as number) ?? null, hi: (w.gunw_context.ci_high as number) ?? null })}</p> : null}
          </>
        ) : null}
        <h3>{t("s.ref.title")}</h3>
        <p><span className={`tag tag--${data.references.status}`}>{t(`s.ref.${data.references.status}`)}</span></p>
        <dl className="facts">
          <dt>{t("s.ref.unit")}</dt><dd>{t("s.ref.unit_text", { k: 3, m: 60 })}</dd>
          <dt>{t("s.ref.sampled")}</dt><dd>{Object.entries(data.references.n_units_sampled).map(([k, v]) => `${t(`s.ref.stratum.${k}`)} : ${v}`).join(" · ") || "—"}</dd>
          <dt>{t("s.ref.annotated")}</dt><dd>{data.references.n_annotated}</dd>
          <dt>{t("s.ref.missing")}</dt><dd>{data.references.missing.map((k) => t(`missing.${k}`)).join(" ; ") || "—"}</dd>
        </dl>
        <p className="small muted">{t("s.ref.rule")}</p>
        <p className="small">{t("s.ref.packet")} : {data.exports.filter((e) => e.id.startsWith("reference_")).map((e) => <a key={e.id} className="filelink" href={file(e.path)}>{e.path.split("/").pop()} </a>)}</p>
      </Section>

      <Section id="conclusion" n={5}>
        <p className="lede">{t("s.conc.lede")}</p>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t("s.table")}>
          <table className="conclusions">
            <caption className="sr-only">{t("sstep.conclusion")}</caption>
            <thead><tr><th scope="col">{t("s.conc.zone")}</th><th scope="col">{t("s.conc.area")}</th><th scope="col">{t("s.conc.radar")}</th><th scope="col">{t("s.conc.optical")}</th><th scope="col">{t("s.conc.cause")}</th></tr></thead>
            <tbody>
              {data.conclusions.map((c) => {
                const rp = c.radar_params as Record<string, number | string | null>;
                const op = c.optical_params as Record<string, number | null>;
                return (
                  <tr key={c.zone_id} className={zoneOpen === c.zone_id ? "is-sel" : undefined}>
                    <th scope="row">
                      <button type="button" className="link" aria-pressed={zoneOpen === c.zone_id} onClick={() => { setZoneOpen(zoneOpen === c.zone_id ? null : c.zone_id); if (c.centroid) setFocus(c.centroid as [number, number]); }}>{c.zone_id}</button>
                      <br /><span className="small muted">{t(c.label_key)}</span>
                    </th>
                    <td>{f.km2(c.area_km2)}</td>
                    <td>{t(`s.radar.${c.radar_variation}`, { el: rp.n_windows_elevated, n: rp.n_windows_with_baseline, frac: rp.median_flagged_fraction, d: rp.median_study_minus_control_db })}{rp.selection === "recurrence_of_the_same_flags" ? <p className="small muted">{t("s.conc.circular")}</p> : null}{rp.selection === "v2_coherence_recurrence" ? <p className="small muted">{t("s.conc.z1_selection")}</p> : null}</td>
                    <td>{t(`s.opt.${c.optical_visible_change}`)} <span className="small muted">({t("s.opt.pairs", { e: op.n_distinct_optical_pairs_elevated, a: op.n_distinct_optical_pairs_assessed })})</span>
                      {Number(op.n_distinct_optical_pairs_elevated) > 0 ? <p className="small muted">{t("s.opt.outside_dev", { k: op.n_elevated_pairs_with_a_window_outside_development })}</p> : null}</td>
                    <td>{t("s.conc.cause_none")}
                      {zoneOpen === c.zone_id ? (
                        <div className="small"><p><b>{t("s.conc.alternatives")}</b> : {c.alternative_keys.map((k) => t(k)).join(" · ")}</p><p><b>{t("s.conc.collect")}</b> : {c.to_collect_keys.map((k) => t(k)).join(" · ")}</p></div>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="notice">{t("s.conc.not_claimed")}</p>
        <h3>{t("s.limits")}</h3>
        <ul className="limits">{data.limits.map((k) => <li key={k}>{t(k)}</li>)}</ul>
        <h3>{t("s.sources")}</h3>
        <ul className="versions">{data.external_sources.map((s) => <li key={s.id}><a href={s.url} rel="noreferrer">{s.title}</a></li>)}</ul>
        <h3>{t("s.files")}</h3>
        <p className="small">{report ? <a className="filelink" href={file(report.path)}>{t("s.report")}</a> : null}
          {data.exports.filter((e) => ["windows_csv", "quality_csv", "acquisitions_csv", "optical_groups_csv", "verification_zones", "boundary_boundary", "boundary_boundary_review"].includes(e.id)).map((e) => <> · <a key={e.id} className="filelink" href={file(e.path)}>{e.path.split("/").pop()}</a></>)}</p>
      </Section>
    </main>
  );
}
