import type { Finding, Measurement, OpticalComparison, PairResult } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase } from "../state";
import { SeriesChart } from "./SeriesChart";
import { formatMeasurement, intervalText, Value } from "./Value";

export const STEPS = ["question", "site", "observations", "quality", "next"] as const;

function Section({ id, n, children }: { id: (typeof STEPS)[number]; n: number; children: React.ReactNode }) {
  const { t } = useI18n();
  return (
    <section id={`step-${id}`} className={`step step--${id}`} aria-labelledby={`h-${id}`}>
      <h2 id={`h-${id}`} className="step__title"><span className="step__n" aria-hidden="true">{n}</span>{t(`step.${id}`)}</h2>
      {children}
    </section>
  );
}

export function FindingText({ f }: { f: Finding }) {
  const { t } = useI18n();
  return <>{t(`finding.${f.kind}`, f.params)}</>;
}

/** Limits shown next to the results they qualify. */
function Limits({ keys }: { keys: string[] }) {
  const { t } = useI18n();
  if (!keys.length) return null;
  return <ul className="inline-limits">{keys.map((k) => <li key={k}>{t(k)}</li>)}</ul>;
}

function M({ m, kind }: { m: Measurement | null | undefined; kind: Parameters<typeof formatMeasurement>[1] }) {
  const { t, f } = useI18n();
  const ci = intervalText(m, kind, f);
  return <>{formatMeasurement(m, kind, f, t)}{ci ? <span className="muted small"> {ci}</span> : null}</>;
}

export function QuestionSection() {
  const { t } = useI18n();
  const { data } = useCase();
  return (
    <Section id="question" n={1}>
      <p className="lede">{t(data.question_key)}</p>
      <p className="observable"><b>{t(data.method.observable_key)}</b></p>
      <p>{t("question.scope")}</p>
      <p>{t("question.contributions")}</p>
      <p className="muted">{t(data.user_key)}</p>
      <div className="split">
        <div><h3>{t("question.answers")}</h3><p>{t("question.answers.list")}</p></div>
        <div><h3>{t("question.not")}</h3><p>{t("question.not.list")}</p></div>
      </div>
    </Section>
  );
}

export function SiteSection() {
  const { t, f } = useI18n();
  const { data, setPairId, pairId } = useCase();
  const z = (role: string) => data.zones.find((x) => x.role === role);
  const study = z("study_perimeter"), control = z("control_ring"), panels = z("mapped_mining_outside_perimeter");
  const dates = data.acquisitions.flatMap((a) => [a.reference_time.slice(0, 10), a.secondary_time.slice(0, 10)]).sort();
  const osmId = study?.source.match(/\d+/)?.[0] ?? "";
  const usable = data.optical_scenes.filter((s) => s.usable);
  return (
    <Section id="site" n={2}>
      <p>{t(data.site.description_key)}</p>
      <dl className="facts">
        {study ? (<><dt>{t("site.perimeter")}</dt><dd>{t("site.perimeter.text", { osm: osmId, date: study.source_date?.slice(0, 10) ?? null, area: study.area_km2 })}</dd></>) : null}
        {control ? (<><dt>{t("site.control")}</dt><dd>{t("site.control.text", { area: control.area_km2 })}</dd></>) : null}
        {panels ? (<><dt>{t("site.panels")}</dt><dd>{t("site.panels.text", { area: panels.area_km2 })}</dd></>) : null}
        <dt>{t("site.data")}</dt>
        <dd>{data.acquisitions.length ? t("site.data.text", { n: data.acquisitions.length, crid: data.acquisitions[0].crid, from: f.date(dates[0]), to: f.date(dates[dates.length - 1]) }) : t("blocker.no_radar_products")}</dd>
        <dt>{t("site.optical")}</dt>
        <dd>{t("site.optical.text", { n: data.optical_scenes.length, complete: data.optical_search.complete ?? null, matched: data.optical_search.number_matched ?? null, usable: usable.length, last: usable.length ? usable[usable.length - 1].datetime.slice(0, 10) : null })}</dd>
      </dl>
      {data.perimeter_versions.length ? (
        <details>
          <summary>{t("site.versions")}</summary>
          <ul className="versions">{data.perimeter_versions.map((v) => <li key={v.id}><b>{v.label}</b> — {f.km2(v.area_km2)} · {v.used_as} · {v.note}{v.source_date ? ` · ${f.date(v.source_date)}` : ""}</li>)}</ul>
        </details>
      ) : null}
      {data.pairs.length ? (
        <div className="table-wrap">
          <table className="pairs">
            <caption className="sr-only">{t("site.data")}</caption>
            <thead><tr><th scope="col">{t("site.table.geometry")}</th><th scope="col">{t("site.table.dates")}</th><th scope="col">{t("site.table.span")}</th><th scope="col">{t("site.table.status")}</th><th scope="col">{t("site.table.reasons")}</th></tr></thead>
            <tbody>
              {data.pairs.map((p) => {
                const a = data.acquisitions.find((x) => x.pair_id === p.pair_id)!;
                const when = `${f.datetime(a.reference_time)} → ${f.datetime(a.secondary_time)}`;
                return (
                  <tr key={p.pair_id} className={p.pair_id === pairId ? "is-sel" : undefined}>
                    <td>{t(`geometry.${p.direction}`)}</td>
                    <td>{p.status === "ok" ? <button type="button" className="link" onClick={() => setPairId(p.pair_id)} aria-pressed={p.pair_id === pairId}>{when}</button> : when}</td>
                    <td>{t("site.table.days", { d: p.span_days })}</td>
                    <td><span className={`tag tag--${p.status}`}>{t(`status.${p.status}`)}</span></td>
                    <td className="small">{p.reasons.join("; ")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </Section>
  );
}

function PairPicker() {
  const { t, f } = useI18n();
  const { data, pairId, setPairId } = useCase();
  return (
    <label className="picker">
      <span>{t("obs.choose")}</span>
      <select value={pairId ?? ""} onChange={(e) => setPairId(e.target.value)}>
        {data.geometries.map((g) => (
          <optgroup key={g.geometry_id} label={`${t(`geometry.${g.direction}`)} · T${g.track}/F${g.frame}`}>
            {data.pairs.filter((p) => p.geometry_id === g.geometry_id).map((p) => (
              <option key={p.pair_id} value={p.pair_id} disabled={p.status !== "ok"}>
                {f.date(p.reference_date)} → {f.date(p.secondary_date)} ({t("site.table.days", { d: p.span_days })}){p.status !== "ok" ? ` — ${t(`status.${p.status}`)}` : ""}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  );
}

function Indicators({ p }: { p: PairResult }) {
  const { t, f } = useI18n();
  const { data } = useCase();
  const main = p.profiles.find((x) => x.id === data.method.main_profile);
  if (p.status !== "ok" || !main || !p.main) return <p className="notice">{t("obs.not_ok", { reason: p.reasons.join("; ") || t(`status.${p.status}`) })}</p>;
  const fl = `flags_${p.pair_id}`, co = `coh_${p.pair_id}`;
  const su = p.statistical.uncertainty;
  const ru = main.ratio_to_evaluation_rate.uncertainty;
  return (
    <>
      <div className="kpis">
        <div className="kpi kpi--lead"><span className="kpi__k">{t("obs.flagged_area")}</span><Value m={main.study_flagged_area_km2} kind="km2" label={t("obs.flagged_area")} pairId={p.pair_id} layerId={fl} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.flagged_share")}</span><Value m={p.statistical} kind="pct" label={t("obs.flagged_share")} pairId={p.pair_id} layerId={fl} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.eval_rate")}</span><Value m={main.evaluation_rate} kind="pct" label={t("obs.eval_rate")} pairId={p.pair_id} layerId={fl} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.ratio")}</span><Value m={main.ratio_to_evaluation_rate} kind="ratio" label={t("obs.ratio")} pairId={p.pair_id} layerId={fl} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.observable")}</span><Value m={p.main.observable_fraction} kind="pct" label={t("obs.observable")} pairId={p.pair_id} layerId={co} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.threshold")}</span><Value m={main.threshold} kind="num3" label={t("obs.threshold")} pairId={p.pair_id} layerId={co} /></div>
      </div>
      <p className="muted small">
        {su?.kind === "block_bootstrap_interval" ? t("obs.ci", { block: su.block_m ?? null, low: su.low ?? null, high: su.high ?? null }) : t("obs.ci.none", { why: su?.method ?? "" })}{" "}
        {ru?.kind === "block_bootstrap_interval" ? t("obs.ci.ratio", { low: ru.low ?? null, high: ru.high ?? null }) : ""}{" "}
        {t("obs.calib_note")} ({f.pct(main.calibration_rate.value, 2)})
      </p>
      <Limits keys={["limit.observable_is_relative", "limit.threshold_is_selection"]} />
    </>
  );
}

function Sensitivity({ p }: { p: PairResult }) {
  const { t, f } = useI18n();
  const { data } = useCase();
  if (p.status !== "ok") return null;
  const order = data.method.controls.map((c) => c.id);
  const rows = [...p.profiles].sort((a, b) => order.indexOf(a.control_id) - order.indexOf(b.control_id) || a.quantile - b.quantile);
  return (
    <details className="sensitivity">
      <summary><h3>{t("obs.sensitivity.title")}</h3></summary>
      <p className="muted small">{t("obs.sensitivity.desc")}</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th scope="col">{t("obs.sens.control")}</th><th scope="col">{t("obs.sens.quantile")}</th><th scope="col">{t("obs.sens.threshold")}</th><th scope="col">{t("obs.sens.area")}</th><th scope="col">{t("obs.sens.fraction")}</th><th scope="col">{t("obs.sens.eval")}</th><th scope="col">{t("obs.sens.ratio")}</th><th scope="col">{t("obs.sens.exceeds")}</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className={r.id === data.method.main_profile ? "is-sel" : undefined}>
                <td>{t(`control.${r.control_id}`)}</td><td>{f.pct(r.quantile, 1)}</td><td>{f.num(r.threshold.value, 3)}</td>
                <td>{f.km2(r.study_flagged_area_km2.value)}</td><td>{f.pct(r.study_flagged_fraction.value, 2)}</td>
                <td>{f.pct(r.evaluation_rate.value, 2)}</td><td><M m={r.ratio_to_evaluation_rate} kind="ratio" /></td>
                <td>{r.exceeds_control == null ? "—" : t(r.exceeds_control ? "yes" : "no")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="split">
        <div>
          <h3>{t("obs.perimeter.title")}</h3>
          <ul className="plain">
            {["eroded_1px", "dilated_1px", "with_panels_2020"].map((k) => (
              <li key={k}>{t(`perim.${k}`)}{t("punct.colon")}{f.km2(p.perimeter_sensitivity[`${k}:area`]?.value)} ({f.pct(p.perimeter_sensitivity[`${k}:fraction`]?.value, 2)})</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>{t("obs.stability.title")}</h3>
          <ul className="plain">
            {Object.entries(p.zone_stability).map(([k, m]) => <li key={k}>{t(`stab.${k}`)}{t("punct.colon")}{k.startsWith("clusters") ? f.pct(m.value, 0) : f.num(m.value, 2)}</li>)}
          </ul>
        </div>
      </div>
    </details>
  );
}

function Clusters({ p }: { p: PairResult }) {
  const { t, f } = useI18n();
  const { setFocus, data } = useCase();
  if (p.status !== "ok") return null;
  const min = Number(data.method.parameters["method.min_cluster_km2"] ?? 0.01);
  return (
    <div className="clusters">
      <h3>{t("obs.clusters")}</h3>
      <p className="muted small">{t("obs.clusters.desc", { n: p.n_clusters, min, shown: p.clusters_shown.length })}</p>
      {p.clusters_shown.length === 0 ? <p className="notice">{t("obs.clusters.none")}</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">{t("obs.cl.area")}</th><th scope="col">{t("obs.cl.where")}</th><th scope="col">{t("obs.cl.coh")}</th><th scope="col">{t("obs.cl.repeat")}</th><th scope="col">{t("obs.cl.retained")}</th></tr></thead>
            <tbody>
              {p.clusters_shown.map((c) => {
                const [lon, lat] = c.centroid as [number, number];
                return (
                  <tr key={c.id}>
                    <td>{f.km2(c.area_km2)}</td>
                    <td><button type="button" className="link" onClick={() => setFocus([lon, lat])} aria-label={`${t("obs.cl.show")} ${f.coord(lon, lat)}`}>{f.coord(lon, lat)}</button></td>
                    <td>{f.num(c.median_coherence, 2)}</td>
                    <td>{c.pairs_same_geometry_overlapping == null ? t("value.not_measured") : t("obs.cl.repeat.value", { k: c.pairs_same_geometry_overlapping, n: c.pairs_same_geometry_observed ?? null })}</td>
                    <td>{c.retained_at_lower_quantile == null ? "—" : t(c.retained_at_lower_quantile ? "yes" : "no")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function ObservationsSection() {
  const { t, f } = useI18n();
  const { data, pairId } = useCase();
  const p = data.pairs.find((x) => x.pair_id === pairId);
  const kinds = ["study_vs_control", "threshold_sensitivity", "control_sensitivity", "inner_vs_outer_ring", "panels_vs_control", "verification_zones"];
  const findings = data.findings.filter((x) => kinds.includes(x.kind));
  return (
    <Section id="observations" n={3}>
      <h3>{t("findings.title")}</h3>
      <ul className="findings">
        {findings.map((x) => <li key={x.id} id={`finding-${x.id}`}><FindingText f={x} /></li>)}
      </ul>
      <Limits keys={["limit.coherence_contributions", "limit.window_length"]} />
      <PairPicker />
      {p ? (<><h3>{t("obs.indicators")}</h3><Indicators p={p} /><Sensitivity p={p} /></>) : null}
      <SeriesChart />
      <div className="geoms">
        <h3>{t("obs.recurrence.title")}</h3>
        {data.geometries.flatMap((g) => g.recurrence.map((r) => (
          <div key={`${g.geometry_id}-${r.span_days}`}>
            <p>{t("obs.rec.text", { geom: `${t(`geometry.${g.direction}`)} · T${g.track}`, n: r.pair_ids.length, min: r.observed_pairs_min ?? null, max: r.observed_pairs_max ?? null,
              ever: r.flagged_ever_km2.value, half: r.flagged_half_or_more_km2.value, disjoint: r.flagged_half_or_more_disjoint_km2.value })}</p>
            <p className="muted small">{t("obs.rec.gaps", { gaps: r.gaps.map((x) => `${f.date(x[0])} → ${f.date(x[1])}`).join(" ; ") })}</p>
          </div>
        )))}
      </div>
      {p ? <Clusters p={p} /> : null}
    </Section>
  );
}

function OpticalTable({ mode }: { mode: "strict" | "exploratory" }) {
  const { t, f } = useI18n();
  const { data, setPairId } = useCase();
  const rows = data.pairs.filter((p) => p.status === "ok").map((p) => [p, p.optical.find((o) => o.mode === mode)] as [PairResult, OpticalComparison | undefined]);
  return (
    <div className="table-wrap">
      <table>
        <caption className="caption">{t(`quality.optical.${mode}`)}</caption>
        <thead><tr>
          <th scope="col">{t("quality.optical.cols.pair")}</th><th scope="col">{t("quality.optical.cols.optical")}</th><th scope="col">{t("quality.optical.cols.joint")}</th>
          <th scope="col">{t("quality.optical.cols.table")}</th><th scope="col">{t("quality.optical.cols.p_r")}</th><th scope="col">{t("quality.optical.cols.p_nr")}</th>
          <th scope="col">{t("quality.optical.cols.ratio")}</th><th scope="col">{t("quality.optical.cols.jaccard")}</th><th scope="col">{t("quality.optical.cols.scl7")}</th><th scope="col">{t("quality.optical.cols.hyp")}</th>
        </tr></thead>
        <tbody>
          {rows.map(([p, o]) => (
            <tr key={p.pair_id}>
              <td><button type="button" className="link" onClick={() => setPairId(p.pair_id)}>{f.date(p.reference_date)} → {f.date(p.secondary_date)}</button> <span className="muted small">({t("site.table.days", { d: p.span_days })})</span></td>
              {o?.status === "ok" ? (
                <>
                  <td className="small">{f.date(o.before_datetime)} (−{t("site.table.days", { d: f.num(o.gap_days_before, 1) })}) / {f.date(o.after_datetime)} (+{t("site.table.days", { d: f.num(o.gap_days_after, 1) })})</td>
                  <td>{f.pct(o.joint_observable_fraction.value, 0)}</td>
                  <td className="small">{o.table ? `${o.table.n11} / ${o.table.n10} / ${o.table.n01} / ${o.table.n00}` : "—"}</td>
                  <td>{f.pct(o.p_optical_given_radar.value, 1)}</td>
                  <td>{f.pct(o.p_optical_given_not_radar.value, 2)}</td>
                  <td><Value m={o.association_ratio} kind="ratio" label={t("quality.optical.cols.ratio")} pairId={p.pair_id} layerId={`opt_${p.pair_id}`} /></td>
                  <td>{f.num(o.jaccard.value, 3)}</td>
                  <td>{formatMeasurement(o.ratio_with_unclassified_scl, "ratio", f, t)}</td>
                  <td className="small">{Object.entries(o.spectral_hypotheses ?? {}).filter(([, v]) => v).map(([k, v]) => `${t(k)} ${v}`).join(" · ")}</td>
                </>
              ) : (
                <td colSpan={9} className="muted small">{t(`optical.status.${o?.status ?? "no_scene_pair"}`)}{o?.reason ? ` — ${o.reason}` : ""}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function QualitySection() {
  const { t, f } = useI18n();
  const { data, setPairId } = useCase();
  const cross = data.cross_geometry;
  const fd = (kind: string) => data.findings.filter((x) => x.kind === kind);
  return (
    <Section id="quality" n={4}>
      <h3>{t("quality.levels")}</h3>
      <p className="muted small">{t("level.scale")}</p>
      <ul className="levels">
        {data.validation.map((v) => (
          <li key={v.observable} className={`level level--${v.level}`}>
            <div className="level__head"><span>{t(`observable.${v.observable}`)}</span><strong>{t(`level.${v.level}`)}</strong></div>
            <div className="level__body">
              {v.criteria.length ? <p><b>{t("criteria.title")}{t("punct.colon")}</b>{v.criteria.map((k) => t(k)).join(" ; ")}</p> : null}
              {v.evidence_keys.length ? <p><b>{t("quality.evidence")}{t("punct.colon")}</b>{v.evidence_keys.map((k) => t(k)).join(" ; ")}</p> : null}
              {v.missing_keys.length ? <p><b>{t("quality.missing")}{t("punct.colon")}</b>{v.missing_keys.map((k) => t(k)).join(" ; ")}</p> : null}
            </div>
          </li>
        ))}
      </ul>
      <h3>{t("quality.cross")}</h3>
      <p className="muted small">{t("quality.cross.rule")}</p>
      {fd("cross_geometry").map((x) => <p key={x.id}><FindingText f={x} /></p>)}
      {cross.matches.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">{t("quality.cross.cols.a")}</th><th scope="col">{t("quality.cross.cols.b")}</th><th scope="col">{t("quality.cross.cols.overlap")}</th><th scope="col">{t("quality.cross.cols.table")}</th><th scope="col">{t("quality.cross.cols.p")}</th><th scope="col">{t("quality.cross.cols.ratio")}</th><th scope="col">{t("quality.cross.cols.jaccard")}</th></tr></thead>
            <tbody>
              {cross.matches.map((m) => {
                const a = data.pairs.find((p) => p.pair_id === m.pair_a)!, b = data.pairs.find((p) => p.pair_id === m.pair_b)!;
                const asc = a.direction === "ascending" ? a : b, desc = a.direction === "ascending" ? b : a;
                return (
                  <tr key={m.pair_a + m.pair_b}>
                    <td><button type="button" className="link" onClick={() => setPairId(asc.pair_id)}>{f.date(asc.reference_date)} → {f.date(asc.secondary_date)}</button></td>
                    <td><button type="button" className="link" onClick={() => setPairId(desc.pair_id)}>{f.date(desc.reference_date)} → {f.date(desc.secondary_date)}</button></td>
                    <td>{t("site.table.days", { d: f.num(m.overlap_days, 1) })}</td>
                    <td className="small">{`${m.table.n11} / ${m.table.n10} / ${m.table.n01} / ${m.table.n00}`}</td>
                    <td>{f.pct(m.p_b_given_a.value, 1)}</td>
                    <td><M m={m.association_ratio} kind="ratio" /></td>
                    <td>{f.num(m.jaccard.value, 3)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      <h3>{t("quality.optical")}</h3>
      <p className="muted small">{t("quality.optical.desc")}</p>
      {fd("optical_association").map((x) => <p key={x.id}><FindingText f={x} /></p>)}
      <OpticalTable mode="strict" />
      <details><summary>{t("quality.optical.exploratory")}</summary><OpticalTable mode="exploratory" /></details>
      <Limits keys={["limit.optical_is_cross_sensor", "limit.spectral_hypotheses"]} />
      <h3>{t("quality.los")}</h3>
      {fd("los_reported").map((x) => <p key={x.id}><FindingText f={x} /></p>)}
      <Limits keys={["limit.los_not_interpreted"]} />
      <h3>{t("quality.pairs")}</h3>
      <ul className="findings">{[...fd("pairs_not_used"), ...fd("long_span_pairs"), ...fd("shared_acquisition"), ...fd("optical_coverage")].map((x) => <li key={x.id} id={`finding-${x.id}`}><FindingText f={x} /></li>)}</ul>
      <h3>{t("quality.limits")}</h3>
      <ul className="limits">{data.limits.map((k) => <li key={k}>{t(k)}</li>)}</ul>
    </Section>
  );
}

export function NextSection() {
  const { t, f } = useI18n();
  const { data, setFocus } = useCase();
  const byId = new Map(data.findings.map((x) => [x.id, x]));
  const geomName = (gid: string) => {
    const g = data.geometries.find((x) => x.geometry_id === gid);
    return g ? `${t(`geometry.${g.direction}`)} · T${g.track}` : gid;
  };
  return (
    <Section id="next" n={5}>
      {data.dossiers.length ? <h3>{t("dossier.title")}</h3> : null}
      {data.dossiers.map((d) => {
        const [lon, lat] = d.centroid as [number, number];
        const obs = d.observation as Record<string, string | number | null>;
        const geoms = Object.keys(obs).filter((k) => k.startsWith("flagged_pairs_")).map((k) => k.replace("flagged_pairs_", ""));
        return (
          <article key={d.id} className="dossier" id={`dossier-${d.id}`} aria-labelledby={`h-dossier-${d.id}`}>
            <h4 id={`h-dossier-${d.id}`}>{d.id} — {f.km2(d.area_km2)} · {f.coord(lon, lat)}</h4>
            <dl className="facts">
              <dt>{t("dossier.zone")}</dt><dd>{t(`zone.${d.zone}`)}{d.landcover ? ` · ${t("dossier.landcover")}${t("punct.colon")}${d.landcover}` : ""}</dd>
              <dt>{t("dossier.observation")}</dt>
              <dd>
                <ul className="plain">
                  {geoms.map((g) => <li key={g}>{t("dossier.flagged", { geom: geomName(g), k: obs[`flagged_pairs_${g}`], n: obs[`observed_pairs_${g}`] })}</li>)}
                  <li>{Number(obs.strict_optical_comparisons) > 0 ? t("dossier.optical", { k: obs.strict_optical_comparisons, share: obs.median_optical_change_share }) : t("dossier.no_optical")}</li>
                  {obs.spectral_hypotheses ? <li>{String(obs.spectral_hypotheses).split(", ").map((x) => { const [k, v] = x.split(":"); return `${t(k)} (${v})`; }).join(" · ")}</li> : null}
                </ul>
              </dd>
              <dt>{t("dossier.evidence")}</dt><dd className="small">{d.dates.map((x) => `${f.date(x[0])} → ${f.date(x[1])}`).join(" ; ")}</dd>
              <dt>{t("dossier.alternatives")}</dt><dd><ul className="plain">{d.alternative_keys.map((k) => <li key={k}>{t(k)}</li>)}</ul></dd>
              <dt>{t("dossier.collect")}</dt><dd><ul className="plain">{d.to_collect_keys.map((k) => <li key={k}>{t(k)}</li>)}</ul></dd>
            </dl>
            <button type="button" className="btn" onClick={() => setFocus([lon, lat])}>{t("obs.cl.show")}</button>
          </article>
        );
      })}
      <h3>{t("next.title")}</h3>
      <ol className="checks">
        {data.next_checks.map((c) => (
          <li key={c.id}>
            <p>{t(`next.${c.kind}`, c.params)}</p>
            <p className="muted small">{t("next.because")}{t("punct.colon")}{c.because.map((b) => {
              const fnd = byId.get(b);
              if (fnd) return <a key={b} href={`#finding-${b}`} className="link">{t(`finding.${fnd.kind}`, fnd.params)}</a>;
              if (data.dossiers.some((d) => d.id === b)) return <a key={b} href={`#dossier-${b}`} className="link">{b}</a>;
              return <span key={b}>{t(b)}</span>;
            })}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

export function SourcesSection() {
  const { t, f } = useI18n();
  const { data, pairId, file } = useCase();
  const acq = data.acquisitions.find((a) => a.pair_id === pairId);
  const m = data.manifest;
  const roles = m ? Object.entries(m.inputs.reduce<Record<string, number>>((acc, x) => ({ ...acc, [x.role]: (acc[x.role] ?? 0) + 1 }), {})).map(([k, v]) => `${k} ${v}`).join(", ") : "";
  const pairExports = data.exports.filter((e) => pairId && e.id.endsWith(pairId));
  const globalExports = data.exports.filter((e) => !e.id.includes("GUNW_"));
  return (
    <section id="sources" className="sources" aria-labelledby="h-sources">
      <h2 id="h-sources">{t("sources.title")}</h2>
      <div className="sources__grid">
        <div>
          <h3>{t("sources.method")}</h3>
          <p>{t("method.text")}</p>
          <details><summary>{t("sources.params")} ({data.method.id} v{data.method.version})</summary>
            <dl className="kv">{Object.entries(data.method.parameters).map(([k, v]) => (<div key={k}><dt>{k}</dt><dd>{JSON.stringify(v)}</dd></div>))}</dl>
          </details>
          <details><summary>{t("sources.controls")}</summary>
            <ul className="plain">{data.method.controls.map((c) => <li key={c.id}><b>{t(c.label_key)}</b> — {f.km2(c.area_km2)} · {Object.entries(c.landcover_share).map(([k, v]) => `${k} ${f.pct(v, 0)}`).join(", ")}</li>)}</ul>
          </details>
          <details><summary>{t("sources.autocorr")}</summary>
            <p className="small">{Object.entries(data.method.autocorrelation).map(([k, v]) => `${k}: ${f.num(v ?? null, 2)}`).join(" · ")}</p>
            <p className="small">{data.method.block_size_justification}</p>
          </details>
          <details><summary>{t("sources.reused")}</summary><ul>{data.method.reused_modules.map((r) => <li key={r}>{r}</li>)}</ul></details>
        </div>
        <div>
          <h3>{t("sources.refs")}</h3>
          <ul className="refs">
            {data.references.map((r) => (
              <li key={r.id}>
                <a className="link" href={r.url} target="_blank" rel="noreferrer">{r.name}</a>
                <span className="small muted">{r.provider} · {r.license}</span>
                <span className="small"><b>{t("sources.supports")}{t("punct.colon")}</b>{t(r.supports_key)}</span>
                <span className="small"><b>{t("sources.cannot")}{t("punct.colon")}</b>{t(r.cannot_support_key)}</span>
              </li>
            ))}
          </ul>
        </div>
        {acq ? (
          <div>
            <h3>{t("sources.pair")}</h3>
            <dl className="kv">
              <div><dt>{t("sources.granule")}</dt><dd className="mono-break">{acq.granule_id}</dd></div>
              <div><dt>{t("sources.version")}</dt><dd>{acq.product_version} · {acq.crid} ({acq.maturity})</dd></div>
              <div><dt>{t("sources.software")}</dt><dd>{acq.software_version} / {acq.product_specification_version}</dd></div>
              <div><dt>{t("sources.processed")}</dt><dd>{acq.processing_datetime}</dd></div>
              <div><dt>{t("sources.looks")}</dt><dd>{acq.looks.wrapped_azimuth_looks} × {acq.looks.wrapped_range_looks}</dd></div>
              <div><dt>DOI</dt><dd>{acq.doi}</dd></div>
              <div><dt>{t("trace.file")}</dt><dd>{t("sources.bytes", { mb: f.num((acq.bytes_transferred ?? 0) / 1e6, 1) })}</dd></div>
            </dl>
          </div>
        ) : null}
        {m ? (
          <div>
            <h3>{t("sources.manifest")}</h3>
            <dl className="kv">
              <div><dt>{t("sources.run")}</dt><dd>{m.run_id} ({f.num(m.duration_s, 0)} s, Python {m.python})</dd></div>
              <div><dt>{t("sources.commit")}</dt><dd className="mono-break">{m.code_commit ?? "—"}{m.code_dirty ? " (+)" : ""}</dd></div>
              <div><dt>config</dt><dd className="mono-break">sha256 {m.config_sha256.slice(0, 16)}…</dd></div>
              <div><dt>in</dt><dd>{t("sources.inputs", { n: m.inputs.length, roles })}</dd></div>
              <div><dt>out</dt><dd>{t("sources.outputs", { n: m.outputs.length })}</dd></div>
            </dl>
          </div>
        ) : null}
      </div>
      <h3 id="exports">{t("exports.title")}</h3>
      <ul className="exports">
        <li><a className="link" href={file("case.json")} download>{t("export.case_json")}</a> <span className="muted small">{t("export.global")}</span></li>
        {globalExports.map((e) => <li key={e.id}><a className="link" href={file(e.path)} download>{t(e.description_key)}</a> <span className="muted small">{t("export.global")}</span></li>)}
        {pairExports.map((e) => <li key={e.id}><a className="link" href={file(e.path)} download>{t(e.description_key)}</a> <span className="muted small">{t("export.for_pair")}</span></li>)}
      </ul>
    </section>
  );
}
