import type { Finding, PairResult } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase } from "../state";
import { SeriesChart } from "./SeriesChart";
import { Value } from "./Value";

function s2date(id: string | null, f: ReturnType<typeof useI18n>["f"]): string {
  const d = id?.split("_")[2];
  return d && d.length === 8 ? f.date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`) : "—";
}

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

export function QuestionSection() {
  const { t } = useI18n();
  const { data } = useCase();
  return (
    <Section id="question" n={1}>
      <p className="lede">{t(data.question_key)}</p>
      <p>{t("question.scope")}</p>
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
        <dd>{data.optical_scenes.length ? t("site.optical.text", { n: data.optical_scenes.length }) : t("blocker.no_optical_reference")}</dd>
      </dl>
      {data.acquisitions.length ? (
        <div className="table-wrap">
          <table className="pairs">
            <caption className="sr-only">{t("site.data")}</caption>
            <thead><tr><th>{t("site.table.geometry")}</th><th>{t("site.table.dates")}</th><th>{t("site.table.span")}</th><th>{t("site.table.status")}</th></tr></thead>
            <tbody>
              {data.pairs.map((p) => (
                <tr key={p.pair_id} className={p.pair_id === pairId ? "is-sel" : undefined}>
                  <td>{t(`geometry.${data.acquisitions.find((a) => a.pair_id === p.pair_id)?.direction}`)}</td>
                  <td>
                    {p.status === "ok"
                      ? <button type="button" className="link" onClick={() => setPairId(p.pair_id)} aria-pressed={p.pair_id === pairId}>{f.date(p.reference_date)} → {f.date(p.secondary_date)}</button>
                      : <span>{f.date(p.reference_date)} → {f.date(p.secondary_date)}</span>}
                  </td>
                  <td>{t("site.table.days", { d: p.span_days })}</td>
                  <td><span className={`tag tag--${p.status}`}>{t(`status.${p.status}`)}</span></td>
                </tr>
              ))}
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
  const { t } = useI18n();
  const study = p.zones.find((z) => z.zone_id === "study");
  if (p.status !== "ok" || !study) return <p className="notice">{t("obs.not_ok", { reason: p.reason ?? t(`status.${p.status}`) })}</p>;
  const flagsLayer = `flags_${p.pair_id}`, cohLayer = `coh_${p.pair_id}`;
  const ratio = study.flagged_fraction_of_observable.value != null && p.control_flag_rate.value
    ? { value: study.flagged_fraction_of_observable.value / p.control_flag_rate.value, unit: "ratio", status: "measured" as const, uncertainty: null }
    : { value: null, unit: "ratio", status: "not_measured" as const, reason: "no control rate" };
  const sens = p.study_flagged_area_sensitivity;
  return (
    <>
      <div className="kpis">
        <div className="kpi kpi--lead"><span className="kpi__k">{t("obs.flagged_area")}</span><Value m={study.flagged_area_km2} kind="km2" label={t("obs.flagged_area")} pairId={p.pair_id} layerId={flagsLayer} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.flagged_share")}</span><Value m={study.flagged_fraction_of_observable} kind="pct" label={t("obs.flagged_share")} pairId={p.pair_id} layerId={flagsLayer} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.ratio")}</span><Value m={ratio} kind="ratio" label={t("obs.ratio")} pairId={p.pair_id} layerId={flagsLayer} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.observable")}</span><Value m={study.observable_fraction} kind="pct" label={t("obs.observable")} pairId={p.pair_id} layerId={cohLayer} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.threshold")}</span><Value m={p.threshold} kind="num3" label={t("obs.threshold")} pairId={p.pair_id} layerId={cohLayer} /></div>
        <div className="kpi"><span className="kpi__k">{t("obs.control_rate")}</span><Value m={p.control_flag_rate} kind="pct" label={t("obs.control_rate")} pairId={p.pair_id} layerId={flagsLayer} /></div>
      </div>
      <p className="muted small">{t("obs.sensitivity", { low: sens["0.005"]?.value ?? null, high: sens["0.05"]?.value ?? null })}</p>
    </>
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
            <thead><tr><th>{t("obs.cl.area")}</th><th>{t("obs.cl.where")}</th><th>{t("obs.cl.coh")}</th><th>{t("obs.cl.other")}</th><th>{t("obs.cl.optical")}</th><th>{t("obs.cl.reading")}</th></tr></thead>
            <tbody>
              {p.clusters_shown.map((c) => (
                <tr key={c.id}>
                  <td>{f.km2(c.area_km2)}</td>
                  <td><button type="button" className="link" onClick={() => setFocus(c.centroid)} aria-label={`${t("obs.cl.show")} ${f.coord(c.centroid[0], c.centroid[1])}`}>{f.coord(c.centroid[0], c.centroid[1])}</button></td>
                  <td>{f.num(c.median_coherence, 2)}</td>
                  <td>{c.recurrence_in_other_pairs == null ? t("value.not_measured") : f.pct(c.recurrence_in_other_pairs, 0)}</td>
                  <td>{c.optical_change_fraction == null ? t("value.not_measured") : f.pct(c.optical_change_fraction, 0)}</td>
                  <td>{c.optical_diagnostics?.indicative_key ? t(String(c.optical_diagnostics.indicative_key)) : t("value.not_measured")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function ObservationsSection() {
  const { t } = useI18n();
  const { data, pairId, setPairId, setFocus } = useCase();
  const p = data.pairs.find((x) => x.pair_id === pairId);
  const findings = data.findings.filter((f) => ["study_rate_vs_control", "inner_vs_outer_ring", "panels_outside_vs_study", "recurrent_cluster"].includes(f.kind));
  return (
    <Section id="observations" n={3}>
      <h3>{t("findings.title")}</h3>
      <ul className="findings">
        {findings.map((f) => (
          <li key={f.id} id={`finding-${f.id}`}>
            <FindingText f={f} />
            {f.kind === "recurrent_cluster" ? (
              <> <button type="button" className="link small" onClick={() => { setPairId(String(f.params.pair_id)); setFocus([Number(f.params.lon), Number(f.params.lat)]); }}>{t("trace.show")}</button></>
            ) : null}
          </li>
        ))}
      </ul>
      <PairPicker />
      {p ? (<><h3>{t("obs.indicators")}</h3><Indicators p={p} /></>) : null}
      <SeriesChart />
      <div className="geoms">
        <h3>{t("obs.geometries")}</h3>
        <dl className="facts facts--grid">
          {data.geometries.map((g) => (
            <div key={g.geometry_id}>
              <dt>{t(`geometry.${g.direction}`)} · T{g.track} ({g.recurrence_pairs.length})</dt>
              <dd>{t("obs.geom.ever")}{t("punct.colon")}<Value m={g.study_area_flagged_ever_km2} kind="km2" label={t("obs.geom.ever")} layerId={g.recurrence_layer_id ?? undefined} /></dd>
              <dd>{t("obs.geom.half")}{t("punct.colon")}<Value m={g.study_area_flagged_half_or_more_km2} kind="km2" label={t("obs.geom.half")} layerId={g.recurrence_layer_id ?? undefined} /></dd>
            </div>
          ))}
        </dl>
      </div>
      {p ? <Clusters p={p} /> : null}
    </Section>
  );
}

export function QualitySection() {
  const { t, f } = useI18n();
  const { data, setPairId } = useCase();
  const cross = data.cross_geometry;
  const los = data.findings.find((x) => x.kind === "los_summary");
  const optFinding = data.findings.find((x) => x.kind === "optical_association");
  const other = data.findings.filter((x) => ["pairs_not_used", "long_span_pairs", "cross_geometry"].includes(x.kind));
  return (
    <Section id="quality" n={4}>
      <h3>{t("quality.levels")}</h3>
      <p className="muted small">{t("level.scale")}</p>
      <ul className="levels">
        {data.validation.map((v) => (
          <li key={v.observable} className={`level level--${v.level}`}>
            <div className="level__head"><span>{t(`observable.${v.observable}`)}</span><strong>{t(`level.${v.level}`)}</strong></div>
            <div className="level__body">
              {v.evidence_keys.length ? <p><b>{t("quality.evidence")}{t("punct.colon")}</b> {v.evidence_keys.map((k) => t(k)).join(" ; ")}</p> : null}
              {v.missing_keys.length ? <p><b>{t("quality.missing")}{t("punct.colon")}</b> {v.missing_keys.map((k) => t(k)).join(" ; ")}</p> : null}
            </div>
          </li>
        ))}
      </ul>
      {cross.status === "ok" ? (
        <>
          <h3>{t("quality.cross")}</h3>
          <p>{t("quality.cross.text", { rho: cross.spearman_recurrence_study.value, lift: cross.lift_frequent_change.value, jac: cross.jaccard_frequent_change.value })}</p>
        </>
      ) : null}
      <h3>{t("quality.optical")}</h3>
      {optFinding ? <p><FindingText f={optFinding} /></p> : null}
      <p className="muted small">{t("quality.optical.desc")}</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>{t("quality.optical.cols.pair")}</th><th>{t("quality.optical.cols.scenes")}</th><th>{t("quality.optical.cols.lift")}</th><th>{t("quality.optical.cols.p")}</th><th>{t("quality.optical.cols.mndwi")}</th></tr></thead>
          <tbody>
            {data.pairs.filter((p) => p.status === "ok").map((p) => (
              <tr key={p.pair_id}>
                <td><button type="button" className="link" onClick={() => setPairId(p.pair_id)}>{f.date(p.reference_date)} → {f.date(p.secondary_date)}</button></td>
                {p.optical?.status === "ok" ? (
                  <>
                    <td className="small">{s2date(p.optical.before_item, f)} / {s2date(p.optical.after_item, f)}</td>
                    <td><Value m={p.optical.lift} kind="ratio" label={t("quality.optical.cols.lift")} pairId={p.pair_id} layerId={`opt_${p.pair_id}`} /></td>
                    <td>{f.pct(p.optical.p_optical_given_radar.value, 0)}</td>
                    <td>{f.num(p.optical.control_median_d_mndwi?.value ?? null, 3)}</td>
                  </>
                ) : (
                  <td colSpan={4} className="muted">{t(`optical.status.${p.optical?.status ?? "no_scene_pair"}`)}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {los ? (<><h3>{t("quality.los")}</h3><p>{t("quality.los.text", { n: los.params.n_pairs as number, sigma: los.params.median_sigma_cm as number, p95: los.params.max_abs_p95_cm as number })}</p></>) : null}
      <h3>{t("quality.pairs")}</h3>
      <ul className="findings">{other.map((x) => <li key={x.id} id={`finding-${x.id}`}><FindingText f={x} /></li>)}</ul>
      <h3>{t("quality.limits")}</h3>
      <ul className="limits">{data.limits.map((k) => <li key={k}>{t(k)}</li>)}</ul>
    </Section>
  );
}

export function NextSection() {
  const { t } = useI18n();
  const { data, setFocus } = useCase();
  const byId = new Map(data.findings.map((x) => [x.id, x]));
  return (
    <Section id="next" n={5}>
      <h3>{t("next.title")}</h3>
      <ol className="checks">
        {data.next_checks.map((c) => (
          <li key={c.id}>
            <p>{t(`next.${c.kind}`, c.params)}</p>
            {typeof c.params.lon === "number" ? (
              <button type="button" className="btn" onClick={() => setFocus([c.params.lon as number, c.params.lat as number])}>{t("obs.cl.show")}</button>
            ) : null}
            <p className="muted small">{t("next.because")}{t("punct.colon")}{c.because.map((b) => {
              const fnd = byId.get(b);
              return fnd ? <a key={b} href={`#finding-${b}`} className="link">{t(`finding.${fnd.kind}`, fnd.params)}</a> : <span key={b}>{t(b)}</span>;
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
          <details><summary>{t("sources.reused")}</summary><ul>{data.method.reused_modules.map((r) => <li key={r}>{r}</li>)}</ul></details>
        </div>
        <div>
          <h3>{t("sources.refs")}</h3>
          <ul className="refs">
            {data.references.map((r) => (
              <li key={r.id}>
                <a className="link" href={r.url} target="_blank" rel="noreferrer">{r.name}</a>
                <span className="small muted">{r.provider} · {r.license}</span>
                <span className="small"><b>{t("sources.supports")}{t("punct.colon")}</b> {t(r.supports_key)}</span>
                <span className="small"><b>{t("sources.cannot")}{t("punct.colon")}</b> {t(r.cannot_support_key)}</span>
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
              <div><dt>in</dt><dd>{t("sources.inputs", { n: m.inputs.length })}</dd></div>
              <div><dt>out</dt><dd>{t("sources.outputs", { n: m.outputs.length })}</dd></div>
            </dl>
          </div>
        ) : null}
      </div>
      <h3 id="exports">{t("exports.title")}</h3>
      <ul className="exports">
        <li><a className="link" href={file("case.json")} download>{t("export.case_json")}</a> <span className="muted small">{t("export.global")}</span></li>
        {globalExports.map((e) => <li key={e.id}><a className="link" href={file(e.path)} download>{t(e.description_key)}</a> <span className="muted small">{t("export.global")} · {e.id}</span></li>)}
        {pairExports.map((e) => <li key={e.id}><a className="link" href={file(e.path)} download>{t(e.description_key)}</a> <span className="muted small">{t("export.for_pair")}</span></li>)}
      </ul>
    </section>
  );
}
