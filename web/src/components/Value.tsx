import type { Measurement } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase } from "../state";

export type Kind = "km2" | "pct" | "num" | "num1" | "num3" | "cm" | "ratio";

export function formatMeasurement(m: Measurement | null | undefined, kind: Kind, f: ReturnType<typeof useI18n>["f"], t: (k: string) => string): string {
  if (!m) return t("value.unavailable");
  if (m.status !== "measured" || m.value == null) return t(`value.${m.status}`);
  switch (kind) {
    case "km2": return f.km2(m.value);
    case "pct": return f.pct(m.value, m.value !== 0 && Math.abs(m.value) < 0.01 ? 2 : 1);
    case "num1": return f.num(m.value, 1);
    case "num3": return f.num(m.value, 3);
    case "cm": return `${f.num(m.value, 1)} cm`;
    case "ratio": return `×${f.num(m.value, 1)}`;
    default: return f.num(m.value, 2);
  }
}

/** A measured value that can be traced back to its pair, layer and source files. Absent values say why. */
export function Value({ m, kind, label, pairId, layerId }: { m: Measurement | null | undefined; kind: Kind; label: string; pairId?: string; layerId?: string }) {
  const { t, f } = useI18n();
  const { openTrace } = useCase();
  const display = formatMeasurement(m, kind, f, t);
  const absent = !m || m.status !== "measured";
  return (
    <button
      type="button"
      className={absent ? "value value--absent" : "value"}
      onClick={() => openTrace({ label, display, measurement: m ?? undefined, pairId, layerId })}
      aria-label={`${label}: ${display}. ${t("trace.title")}`}
    >
      <span className="value__num">{display}</span>
      {absent && m?.reason ? <span className="value__reason">{m.reason}</span> : null}
    </button>
  );
}
