import { useEffect, useRef } from "react";
import { useI18n } from "../i18nContext";
import { useCase, type ResultKind, type TraceTarget } from "../state";

const FOCUSABLE = "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex='-1'])";
const RESULT_OF: Record<string, ResultKind> = { flags: "flags", coh: "coh", opt: "opt", los: "los", recurrence: "recurrence", observed: "observed" };

/** Modal provenance panel: focus is trapped inside, Escape closes; the caller returns focus to the opener. */
export function TraceDrawer({ target, onClose }: { target: TraceTarget; onClose: () => void }) {
  const { t, f } = useI18n();
  const { data, setPairId, setResult } = useCase();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const panel = ref.current;
    panel?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (!panel.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  const m = target.measurement;
  const acq = target.pairId ? data.acquisitions.find((a) => a.pair_id === target.pairId) : undefined;
  const layer = target.layerId ? data.layers.find((l) => l.id === target.layerId) : undefined;
  const u = m?.uncertainty;
  const unc = !u || u.kind === "not_estimated" ? `${t("value.uncertainty.none")}${u?.method ? ` (${u.method})` : ""}`
    : u.kind === "block_bootstrap_interval" ? `${f.num(u.low ?? null, 4)} – ${f.num(u.high ?? null, 4)} (95 %, ${u.n_blocks} × ${f.num(u.block_m ?? null, 0)} m; ${u.method})`
    : `σ = ${f.num(u.value ?? null, 2)} (${u.method})`;
  const kind = layer?.id.split("_")[0];
  return (
    <div className="trace" role="dialog" aria-modal="true" aria-labelledby="trace-title">
      <div className="trace__scrim" onClick={onClose} />
      <div className="trace__panel" ref={ref}>
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
                {u?.block_size_sensitivity ? (
                  <><dt>{t("trace.blocks")}</dt><dd>{Object.entries(u.block_size_sensitivity).map(([b, v]) => `${b}: ${f.num(v[0], 4)} – ${f.num(v[1], 4)}`).join(" · ")}</dd></>
                ) : null}
              </dl>
            ) : null}
          </li>
          {acq ? (
            <li>
              <span className="trace__k">{t("trace.pair")}</span>
              <strong className="trace__v">{f.datetime(acq.reference_time)} → {f.datetime(acq.secondary_time)}</strong>
              <dl className="trace__dl">
                <dt>{t("site.table.geometry")}</dt><dd>{t(`geometry.${acq.direction}`)} · T{acq.track}/F{acq.frame}</dd>
                <dt>{t("sources.granule")}</dt><dd className="mono-break">{acq.granule_id}</dd>
                <dt>{t("sources.version")}</dt><dd>{acq.product_version} · {acq.crid} ({acq.maturity})</dd>
                <dt>{t("sources.software")}</dt><dd>{acq.software_version} / {acq.product_specification_version}</dd>
                <dt>{t("sources.processed")}</dt><dd>{acq.processing_datetime}</dd>
                <dt>DOI</dt><dd>{acq.doi}</dd>
                <dt>{t("sources.coh_qc")}</dt><dd>{acq.coherence_qc.ok ? "OK" : acq.coherence_qc.reasons.join("; ")}</dd>
                <dt>{t("sources.phase_qc")}</dt><dd>{acq.phase_qc.ok ? "OK" : acq.phase_qc.reasons.join("; ")}</dd>
              </dl>
            </li>
          ) : null}
          {layer ? (
            <li>
              <span className="trace__k">{t("trace.layer")}</span>
              <strong className="trace__v">{t(layer.title_key)}</strong>
              <p className="small">{f.date(layer.date_start)} → {f.date(layer.date_end)}</p>
              {kind && RESULT_OF[kind] ? (
                <button type="button" className="btn" onClick={() => {
                  if (target.pairId) setPairId(target.pairId);
                  setResult(RESULT_OF[kind]);
                  onClose();
                }}>{t("trace.show")}</button>
              ) : null}
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
