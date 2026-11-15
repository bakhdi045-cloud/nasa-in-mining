import { useEffect, useRef } from "react";
import { useI18n } from "../i18nContext";
import { useCase, type TraceTarget } from "../state";

export function TraceDrawer({ target, onClose }: { target: TraceTarget; onClose: () => void }) {
  const { t, f } = useI18n();
  const { data, setPairId, setResult } = useCase();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const m = target.measurement;
  const acq = target.pairId ? data.acquisitions.find((a) => a.pair_id === target.pairId) : undefined;
  const layer = target.layerId ? data.layers.find((l) => l.id === target.layerId) : undefined;
  const u = m?.uncertainty;
  const unc = !u ? t("value.uncertainty.none")
    : u.kind === "sensitivity_range" ? `${f.num(u.low ?? null, 3)} – ${f.num(u.high ?? null, 3)} (${u.method})`
    : u.kind === "empirical_sigma" ? `σ = ${f.num(u.value ?? null, 2)} (${u.method})`
    : t("value.uncertainty.none");
  return (
    <div className="trace" role="dialog" aria-modal="true" aria-labelledby="trace-title">
      <div className="trace__scrim" onClick={onClose} />
      <div className="trace__panel" ref={ref} tabIndex={-1}>
        <header className="trace__head">
          <h2 id="trace-title">{t("trace.title")}</h2>
          <button type="button" className="btn btn--quiet" onClick={onClose}>{t("trace.close")}</button>
        </header>
        <ol className="trace__chain">
          <li>
            <span className="trace__k">{target.label}</span>
            <strong className="trace__v">{target.display}</strong>
            {m ? (
              <dl className="trace__dl">
                <dt>{t("trace.unit")}</dt><dd>{m.unit}</dd>
                <dt>{t("trace.status")}</dt><dd>{t(`value.${m.status}`)}</dd>
                {m.reason ? (<><dt>{t("value.why")}</dt><dd>{m.reason}</dd></>) : null}
                <dt>{t("trace.uncertainty")}</dt><dd>{unc}</dd>
              </dl>
            ) : null}
          </li>
          {acq ? (
            <li>
              <span className="trace__k">{t("trace.pair")}</span>
              <strong className="trace__v">{f.date(acq.reference_time.slice(0, 10))} → {f.date(acq.secondary_time.slice(0, 10))}</strong>
              <dl className="trace__dl">
                <dt>{t("site.table.geometry")}</dt><dd>{t(`geometry.${acq.direction}`)} · T{acq.track}/F{acq.frame}</dd>
                <dt>{t("sources.granule")}</dt><dd className="mono-break">{acq.granule_id}</dd>
                <dt>{t("sources.version")}</dt><dd>{acq.product_version} · {acq.crid} ({acq.maturity})</dd>
                <dt>{t("sources.processed")}</dt><dd>{acq.processing_datetime}</dd>
                <dt>DOI</dt><dd>{acq.doi}</dd>
              </dl>
            </li>
          ) : null}
          {layer ? (
            <li>
              <span className="trace__k">{t("trace.layer")}</span>
              <strong className="trace__v">{t(layer.title_key)}</strong>
              <button type="button" className="btn" onClick={() => {
                if (target.pairId) setPairId(target.pairId);
                const kind = layer.id.split("_")[0];
                setResult(kind === "recurrence" ? "recurrence" : (kind as "flags" | "coh" | "opt" | "los"));
                onClose();
              }}>{t("trace.show")}</button>
            </li>
          ) : null}
          {acq ? (
            <li>
              <span className="trace__k">{t("trace.file")}</span>
              <ul className="trace__files">
                {acq.layers.map((l) => (
                  <li key={l.name}><span>{l.name}</span> <code title={l.sha256}>sha256 {l.sha256.slice(0, 12)}…</code></li>
                ))}
              </ul>
              <a href={acq.source_url} className="link" target="_blank" rel="noreferrer">ASF / Earthdata</a>
            </li>
          ) : null}
        </ol>
      </div>
    </div>
  );
}
