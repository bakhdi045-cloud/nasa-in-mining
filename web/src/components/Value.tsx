import type { Measurement } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase } from "../state";

export type Kind = "km2" | "pct" | "num" | "num1" | "num3" | "cm" | "ratio";

type F = ReturnType<typeof useI18n>["f"];

export function formatMeasurement(m: Measurement | null | undefined, kind: Kind, f: F, t: (k: string) => string): string {
  if (!m) return t("value.unavailable");
  if (m.status !== "measured" || m.value == null) return t(`value.${m.status}`);
  const v = m.value;
  switch (kind) {
    case "km2": return f.km2(v);
    case "pct": return f.pct(v, v !== 0 && Math.abs(v) < 0.01 ? 2 : 1);
    case "num1": return f.num(v, 1);
    case "num3": return f.num(v, 3);
    case "cm": return `${f.num(v, 1)} cm`;
    case "ratio": return `×${f.num(v, v < 10 ? 2 : 1)}`;
    default: return f.num(v, 2);
  }
}

/** Interval text for a measured value, or null when no interval was estimated. */
export function intervalText(m: Measurement | null | undefined, kind: Kind, f: F): string | null {
  const u = m?.uncertainty;
  if (!u || u.kind !== "block_bootstrap_interval" || u.low == null || u.high == null) return null;
  const fmt = (v: number) => (kind === "pct" ? f.pct(v, 2) : kind === "ratio" ? f.num(v, 2) : f.num(v, 3));
  return `[${fmt(u.low)} – ${fmt(u.high)}]`;
}

/** A measured value that can be traced back to its pair, layer and source files. Absent values say why. */
export function Value({ m, kind, label, pairId, layerId, showInterval = true }: {
  m: Measurement | null | undefined; kind: Kind; label: string; pairId?: string; layerId?: string; showInterval?: boolean;
}) {
  const { t, f } = useI18n();
  const { openTrace } = useCase();
  const display = formatMeasurement(m, kind, f, t);
  const ci = showInterval ? intervalText(m, kind, f) : null;
  const absent = !m || m.status !== "measured";
  return (
    <button
      type="button"
      className={absent ? "value value--absent" : "value"}
      onClick={(e) => openTrace({ label, display, measurement: m ?? undefined, pairId, layerId }, e.currentTarget)}
      aria-haspopup="dialog"
      aria-label={`${label}: ${display}${ci ? ` ${ci}` : ""}. ${t("trace.title")}`}
    >
      <span className="value__num">{display}</span>
      {ci ? <span className="value__ci">{ci}</span> : null}
      {absent && m?.reason ? <span className="value__reason">{m.reason}</span> : null}
    </button>
  );
}
