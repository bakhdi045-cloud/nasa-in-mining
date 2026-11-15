import { useMemo, useState } from "react";
import type { PairResult } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase } from "../state";

const W = 640, H = 270, M = { l: 54, r: 16, t: 18, b: 40 };
const DAY = 86_400_000;

function mainProfile(p: PairResult, id: string) {
  return p.profiles.find((x) => x.id === id);
}

export function SeriesChart() {
  const { t, f, lang } = useI18n();
  const { data, pairId, setPairId } = useCase();
  const [hover, setHover] = useState<string | null>(null);
  const geoms = data.geometries.map((g) => g.geometry_id);
  const cls = (gid: string) => `series-${Math.max(0, geoms.indexOf(gid)) + 1}`;
  const mainId = data.method.main_profile;
  const pts = useMemo(() => data.pairs.map((p) => {
    const a = Date.parse(`${p.reference_date}T00:00:00Z`), b = Date.parse(`${p.secondary_date}T00:00:00Z`);
    const mp = p.status === "ok" ? mainProfile(p, mainId) : undefined;
    const u = p.statistical.uncertainty;
    return { p, a, b, mid: (a + b) / 2, v: mp?.study_flagged_fraction.value ?? null, ev: mp?.evaluation_rate.value ?? null,
             lo: u?.kind === "block_bootstrap_interval" ? u.low ?? null : null, hi: u?.kind === "block_bootstrap_interval" ? u.high ?? null : null };
  }), [data.pairs, mainId]);
  if (!pts.length) return null;
  const x0 = Math.min(...pts.map((d) => d.a)) - 2 * DAY, x1 = Math.max(...pts.map((d) => d.b)) + 2 * DAY;
  const vmax = Math.max(0.01, ...pts.map((d) => d.hi ?? d.v ?? 0));
  const yTop = Math.ceil(vmax * 100) / 100 + 0.005;
  const rtl = lang === "ar";
  const X = (ms: number) => M.l + (rtl ? 1 - (ms - x0) / (x1 - x0) : (ms - x0) / (x1 - x0)) * (W - M.l - M.r);
  const Y = (v: number) => H - M.b - (v / yTop) * (H - M.t - M.b);
  const ticks = [0, yTop / 2, yTop];
  const months: number[] = [];
  for (let m = Date.UTC(new Date(x0).getUTCFullYear(), new Date(x0).getUTCMonth() + 1, 1); m <= x1; m = Date.UTC(new Date(m).getUTCFullYear(), new Date(m).getUTCMonth() + 1, 1)) months.push(m);
  const monthFmt = new Intl.DateTimeFormat(lang === "ar" ? "ar-MA" : lang === "fr" ? "fr-FR" : "en-GB", { month: "short", timeZone: "UTC", numberingSystem: "latn" });
  const hovered = pts.find((d) => d.p.pair_id === hover);
  const segments = (gid: string) => {
    const s = pts.filter((d) => d.p.geometry_id === gid && d.v != null && d.p.span_days === 12).sort((a, b) => a.a - b.a);
    const out: (typeof s)[] = [];
    for (const d of s) {
      const last = out[out.length - 1];
      if (last && last[last.length - 1].p.secondary_date === d.p.reference_date) last.push(d);
      else out.push([d]);
    }
    return out.filter((seg) => seg.length > 1);
  };
  return (
    <figure className="chart">
      <figcaption>
        <h3>{t("obs.series")}</h3>
        <p className="muted small">{t("obs.series.desc")}</p>
        <ul className="chart__legend">
          {data.geometries.map((g) => <li key={g.geometry_id}><span className={`dot ${cls(g.geometry_id)}`} />{t(`geometry.${g.direction}`)} · T{g.track}</li>)}
          <li><span className="dash" />{t("obs.eval_rate")}</li>
          <li><span className="gap" />{t("status.rejected_coherence_qc")}</li>
        </ul>
      </figcaption>
      <div className="chart__plot">
        <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label={t("obs.series")}>
          {ticks.map((v) => (
            <g key={v}>
              <line className="grid" x1={M.l} x2={W - M.r} y1={Y(v)} y2={Y(v)} />
              <text className="tick" x={rtl ? W - M.r + 4 : M.l - 8} y={Y(v) + 4} textAnchor={rtl ? "start" : "end"}>{f.pct(v, 1)}</text>
            </g>
          ))}
          {months.map((m) => <text key={m} className="tick" x={X(m)} y={H - M.b + 18} textAnchor="middle">{monthFmt.format(new Date(m))}</text>)}
          {pts.filter((d) => d.p.status !== "ok").map((d) => (
            <rect key={d.p.pair_id} className="gapband" x={Math.min(X(d.a), X(d.b))} width={Math.abs(X(d.b) - X(d.a))} y={M.t} height={H - M.t - M.b}>
              <title>{`${f.date(d.p.reference_date)} → ${f.date(d.p.secondary_date)} : ${t(`status.${d.p.status}`)}`}</title>
            </rect>
          ))}
          {geoms.flatMap((gid) => segments(gid).map((seg, i) => (
            <polyline key={`${gid}-${i}`} className={`line ${cls(gid)}`} points={seg.map((d) => `${X(d.mid)},${Y(d.v!)}`).join(" ")} />
          )))}
          {pts.filter((d) => d.v != null).map((d) => {
            const cx = X(d.mid), cy = Y(d.v!);
            const sel = d.p.pair_id === pairId;
            const label = `${t(`geometry.${d.p.direction}`)}, ${f.date(d.p.reference_date)} → ${f.date(d.p.secondary_date)} (${t("site.table.days", { d: d.p.span_days })}) : ${f.pct(d.v, 2)}`;
            return (
              <g key={d.p.pair_id} className={`pt ${cls(d.p.geometry_id)}${sel ? " pt--sel" : ""}`} role="button" tabIndex={0} aria-label={label} aria-pressed={sel}
                onClick={() => setPairId(d.p.pair_id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPairId(d.p.pair_id); } }}
                onMouseEnter={() => setHover(d.p.pair_id)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(d.p.pair_id)} onBlur={() => setHover(null)}>
                {d.lo != null && d.hi != null ? <line className="ci" x1={cx} x2={cx} y1={Y(d.lo)} y2={Y(d.hi)} /> : null}
                {d.ev != null ? <line className="evtick" x1={cx - 7} x2={cx + 7} y1={Y(d.ev)} y2={Y(d.ev)} /> : null}
                <circle className="hit" cx={cx} cy={cy} r={12} />
                {sel ? <circle className="ring" cx={cx} cy={cy} r={8.5} /> : null}
                {d.p.span_days === 12 ? <circle className="mark" cx={cx} cy={cy} r={5} /> : <rect className="mark" x={cx - 5} y={cy - 5} width={10} height={10} transform={`rotate(45 ${cx} ${cy})`} />}
              </g>
            );
          })}
        </svg>
        {hovered && hovered.v != null ? (
          <div className="tooltip" style={{ left: `${(X(hovered.mid) / W) * 100}%`, top: `${(Y(hovered.v) / H) * 100}%` }} role="status">
            <strong>{f.pct(hovered.v, 2)} {hovered.lo != null ? `[${f.pct(hovered.lo, 2)} – ${f.pct(hovered.hi, 2)}]` : ""}</strong>
            <span>{f.date(hovered.p.reference_date)} → {f.date(hovered.p.secondary_date)} ({t("site.table.days", { d: hovered.p.span_days })})</span>
            <span>{t("obs.eval_rate")}{t("punct.colon")}{f.pct(hovered.ev, 2)}</span>
          </div>
        ) : null}
      </div>
      <details className="chart__table">
        <summary>{t("obs.series.table")}</summary>
        <div className="table-wrap">
          <table>
            <thead><tr><th>{t("site.table.geometry")}</th><th>{t("site.table.dates")}</th><th>{t("site.table.span")}</th><th>{t("obs.flagged_share")}</th><th>IC 95 %</th><th>{t("obs.eval_rate")}</th><th>{t("site.table.status")}</th></tr></thead>
            <tbody>
              {pts.map((d) => (
                <tr key={d.p.pair_id}>
                  <td>{t(`geometry.${d.p.direction}`)}</td>
                  <td>{f.date(d.p.reference_date)} → {f.date(d.p.secondary_date)}</td>
                  <td>{t("site.table.days", { d: d.p.span_days })}</td>
                  <td>{d.v == null ? t("value.not_measured") : f.pct(d.v, 2)}</td>
                  <td>{d.lo == null ? "—" : `${f.pct(d.lo, 2)} – ${f.pct(d.hi, 2)}`}</td>
                  <td>{f.pct(d.ev, 2)}</td>
                  <td>{t(`status.${d.p.status}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
