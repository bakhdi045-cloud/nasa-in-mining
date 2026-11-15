import { useMemo, useState } from "react";
import type { PairResult } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase } from "../state";

const W = 640, H = 260, M = { l: 52, r: 16, t: 18, b: 40 };
const day = 86_400_000;

function share(p: PairResult): number | null {
  const z = p.zones.find((m) => m.zone_id === "study");
  return z?.flagged_fraction_of_observable.value ?? null;
}

export function SeriesChart() {
  const { t, f, lang } = useI18n();
  const { data, pairId, setPairId } = useCase();
  const [hover, setHover] = useState<string | null>(null);
  const geoms = data.geometries.map((g) => g.geometry_id);
  const seriesClass = (gid: string) => `series-${Math.max(0, geoms.indexOf(gid)) + 1}`;
  const pts = useMemo(() => data.pairs.map((p) => {
    const a = Date.parse(`${p.reference_date}T00:00:00Z`), b = Date.parse(`${p.secondary_date}T00:00:00Z`);
    return { p, a, b, mid: (a + b) / 2, v: p.status === "ok" ? share(p) : null };
  }), [data.pairs]);
  if (!pts.length) return null;
  const x0 = Math.min(...pts.map((d) => d.a)) - 2 * day, x1 = Math.max(...pts.map((d) => d.b)) + 2 * day;
  const vmax = Math.max(0.01, ...pts.map((d) => d.v ?? 0));
  const yTop = Math.ceil((vmax * 100) / 1) / 100 + 0.005;
  const rtl = lang === "ar";
  const X = (tms: number) => {
    const u = (tms - x0) / (x1 - x0);
    return M.l + (rtl ? 1 - u : u) * (W - M.l - M.r);
  };
  const Y = (v: number) => H - M.b - (v / yTop) * (H - M.t - M.b);
  const control = data.pairs.find((p) => p.status === "ok")?.control_flag_rate.value ?? null;
  const yTicks = [0, yTop / 2, yTop].map((v) => Math.round(v * 1000) / 1000);
  const months: number[] = [];
  for (let d = new Date(x0); d.getTime() <= x1; d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))) {
    const m = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + (d.getUTCDate() > 1 ? 1 : 0), 1);
    if (m >= x0 && m <= x1 && !months.includes(m)) months.push(m);
  }
  const monthFmt = new Intl.DateTimeFormat(lang === "ar" ? "ar-MA" : lang === "fr" ? "fr-FR" : "en-GB", { month: "short", timeZone: "UTC", numberingSystem: "latn" });
  const hovered = pts.find((d) => d.p.pair_id === hover);

  return (
    <figure className="chart">
      <figcaption>
        <h3>{t("obs.series")}</h3>
        <p className="muted">{t("obs.series.desc")}</p>
        <ul className="chart__legend">
          {data.geometries.map((g) => (
            <li key={g.geometry_id}><span className={`dot ${seriesClass(g.geometry_id)}`} />{t(`geometry.${g.direction}`)} · T{g.track}</li>
          ))}
          <li><span className="dash" />{t("obs.control_rate")}</li>
          <li><span className="gap" />{t("status.rejected_quality")}</li>
        </ul>
      </figcaption>
      <div className="chart__plot">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("obs.series")}>
          {yTicks.map((v) => (
            <g key={v}>
              <line className="grid" x1={M.l} x2={W - M.r} y1={Y(v)} y2={Y(v)} />
              <text className="tick" x={rtl ? W - M.r + 4 : M.l - 8} y={Y(v) + 4} textAnchor={rtl ? "start" : "end"}>{f.pct(v, 1)}</text>
            </g>
          ))}
          {months.map((m) => (
            <text key={m} className="tick" x={X(m)} y={H - M.b + 18} textAnchor="middle">{monthFmt.format(new Date(m))}</text>
          ))}
          {pts.filter((d) => d.p.status !== "ok").map((d) => (
            <rect key={d.p.pair_id} className="gapband" x={Math.min(X(d.a), X(d.b))} width={Math.abs(X(d.b) - X(d.a))} y={M.t} height={H - M.t - M.b}>
              <title>{`${f.date(d.p.reference_date)} → ${f.date(d.p.secondary_date)} : ${t(`status.${d.p.status}`)}`}</title>
            </rect>
          ))}
          {control != null ? <line className="control" x1={M.l} x2={W - M.r} y1={Y(control)} y2={Y(control)} /> : null}
          {geoms.map((gid) => {
            const s = pts.filter((d) => d.p.geometry_id === gid && d.v != null && d.p.span_days === 12).sort((a, b) => a.mid - b.mid);
            return <polyline key={gid} className={`line ${seriesClass(gid)}`} points={s.map((d) => `${X(d.mid)},${Y(d.v!)}`).join(" ")} />;
          })}
          {pts.filter((d) => d.v != null).map((d) => {
            const cx = X(d.mid), cy = Y(d.v!);
            const sel = d.p.pair_id === pairId;
            const label = `${t(`geometry.${data.acquisitions.find((a) => a.pair_id === d.p.pair_id)?.direction ?? "ascending"}`)}, ${f.date(d.p.reference_date)} → ${f.date(d.p.secondary_date)} : ${f.pct(d.v, 2)}`;
            return (
              <g key={d.p.pair_id} className={`pt ${seriesClass(d.p.geometry_id)}${sel ? " pt--sel" : ""}`} role="button" tabIndex={0} aria-label={label} aria-pressed={sel}
                onClick={() => setPairId(d.p.pair_id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPairId(d.p.pair_id); } }}
                onMouseEnter={() => setHover(d.p.pair_id)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(d.p.pair_id)} onBlur={() => setHover(null)}>
                <circle className="hit" cx={cx} cy={cy} r={12} />
                {sel ? <circle className="ring" cx={cx} cy={cy} r={8.5} /> : null}
                {d.p.span_days === 12 ? <circle className="mark" cx={cx} cy={cy} r={5} /> : <rect className="mark" x={cx - 5} y={cy - 5} width={10} height={10} transform={`rotate(45 ${cx} ${cy})`} />}
              </g>
            );
          })}
        </svg>
        {hovered && hovered.v != null ? (
          <div className="tooltip" style={{ left: `${(X(hovered.mid) / W) * 100}%`, top: `${(Y(hovered.v) / H) * 100}%` }} role="status">
            <strong>{f.pct(hovered.v, 2)}</strong>
            <span>{f.date(hovered.p.reference_date)} → {f.date(hovered.p.secondary_date)} ({t("site.table.days", { d: hovered.p.span_days })})</span>
          </div>
        ) : null}
      </div>
      <details className="chart__table">
        <summary>{t("obs.series.table")}</summary>
        <table>
          <thead><tr><th>{t("site.table.geometry")}</th><th>{t("site.table.dates")}</th><th>{t("site.table.span")}</th><th>{t("obs.flagged_share")}</th><th>{t("site.table.status")}</th></tr></thead>
          <tbody>
            {pts.map((d) => (
              <tr key={d.p.pair_id}>
                <td>{d.p.geometry_id}</td>
                <td>{f.date(d.p.reference_date)} → {f.date(d.p.secondary_date)}</td>
                <td>{t("site.table.days", { d: d.p.span_days })}</td>
                <td>{d.v == null ? t("value.not_measured") : f.pct(d.v, 2)}</td>
                <td>{t(`status.${d.p.status}`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
