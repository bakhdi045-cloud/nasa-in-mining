import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fileUrl, loadCase, LoadError, type CaseListItem } from "./api";
import type { MiningCase } from "./contract";
import { LANGS, type Lang } from "./i18n";
import { I18nContext, makeI18n, useI18n } from "./i18nContext";
import { CaseContext, readUrl, RESULT_KINDS, writeUrl, type ResultKind, type TraceTarget } from "./state";
import { MapView } from "./components/MapView";
import { NextSection, ObservationsSection, QualitySection, QuestionSection, SiteSection, SourcesSection, STEPS } from "./components/Sections";
import { TraceDrawer } from "./components/TraceDrawer";

function initialLang(): Lang {
  const u = readUrl().lang;
  if (u === "fr" || u === "en" || u === "ar") return u;
  try {
    const v = window.localStorage.getItem("mining.lang");
    if (v === "fr" || v === "en" || v === "ar") return v;
  } catch { /* storage unavailable: default language */ }
  const nav = (navigator.language || "fr").slice(0, 2);
  return (LANGS as string[]).includes(nav) ? (nav as Lang) : "fr";
}

function Header({ data, list, lang, setLang, inert }: { data: MiningCase | null; list: CaseListItem[]; lang: Lang; setLang: (l: Lang) => void; inert: boolean }) {
  const { t } = useI18n();
  const level = data?.validation.find((v) => v.observable === "low_coherence_location");
  const runs = list.find((c) => c.case_id === data?.case_id)?.runs ?? [];
  const published = list.find((c) => c.case_id === data?.case_id)?.published_run;
  return (
    <header className="masthead" inert={inert || undefined}>
      <a className="skip" href="#main">{t("app.skip")}</a>
      <div className="masthead__top">
        <p className="masthead__brand">NASA in Mining</p>
        <div className="masthead__tools">
          <div className="langs" role="group" aria-label={t("app.language")}>
            {LANGS.map((l) => (
              <button key={l} type="button" lang={l} className={l === lang ? "lang is-on" : "lang"} aria-pressed={l === lang} onClick={() => setLang(l)}>{t(`lang.${l}`)}</button>
            ))}
          </div>
          {runs.length > 1 ? (
            <label className="select-label">
              <span>{t("app.run")}</span>
              <select value={data?.run_id} onChange={(e) => { writeUrl({ run: e.target.value === published ? undefined : e.target.value }); window.location.reload(); }}>
                {runs.map((r) => <option key={r} value={r}>{r}{r === published ? ` (${t("app.run.published")})` : ""}</option>)}
              </select>
            </label>
          ) : null}
          <button type="button" className="btn btn--quiet" onClick={() => window.print()}>{t("app.print")}</button>
        </div>
      </div>
      <h1 className="masthead__title">{t("app.title")}</h1>
      <p className="masthead__tagline">{t("app.tagline")}</p>
      {data ? (
        <>
          <p className="presentation">{t(data.presentation_level_key)}</p>
          <ul className="badges" aria-label={t("app.case")}>
            <li className={`badge badge--${data.data_nature}`}>{t(`nature.${data.data_nature}`)}</li>
            <li className={`badge badge--${data.processing.status}`}>{t(`processing.${data.processing.status}`)}</li>
            {level ? <li className={`badge badge--level-${level.level}`}>{t(`observable.${level.observable}`)}{t("punct.colon")}{t(`level.${level.level}`)}</li> : null}
            <li className="badge">{t("app.run")} {data.run_id}</li>
          </ul>
          <nav className="steps" aria-label={t("app.case")}>
            <ol>{STEPS.map((s, i) => <li key={s}><a href={`#step-${s}`}><span aria-hidden="true">{i + 1}</span>{t(`step.${s}`)}</a></li>)}</ol>
          </nav>
        </>
      ) : null}
    </header>
  );
}

function Unavailable({ data }: { data: MiningCase }) {
  const { t } = useI18n();
  return (
    <main id="main" className="unavailable" aria-labelledby="h-unavail">
      <h2 id="h-unavail">{t("unavailable.title")}</h2>
      <p>{t("unavailable.text")}</p>
      <ul>{(data.processing.blockers ?? []).map((b) => <li key={b}>{t(b)}</li>)}</ul>
      <ul className="limits">{data.limits.map((k) => <li key={k}>{t(k)}</li>)}</ul>
    </main>
  );
}

export function CaseView({ data, onTraceChange }: { data: MiningCase; onTraceChange?: (open: boolean) => void }) {
  const url = readUrl();
  const okPairs = data.pairs.filter((p) => p.status === "ok").map((p) => p.pair_id);
  const preferred = data.dossiers[0]?.evidence.find((e) => okPairs.includes(e));
  const [pairId, setPairIdState] = useState<string | null>(url.pair && okPairs.includes(url.pair) ? url.pair : preferred ?? okPairs[0] ?? null);
  const [result, setResultState] = useState<ResultKind>(RESULT_KINDS.includes(url.layer as ResultKind) ? (url.layer as ResultKind) : "flags");
  const [recurrenceGeometry, setRecurrenceGeometry] = useState<string | null>(data.geometries.find((g) => g.recurrence.length)?.geometry_id ?? null);
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const [trace, setTrace] = useState<TraceTarget | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const file = useCallback((path: string) => fileUrl(data.case_id, path, url.run), [data.case_id, url.run]);
  const setPairId = useCallback((id: string) => {
    setPairIdState(id);
    setResultState((r) => (r === "recurrence" || r === "observed" || r === "none" ? "flags" : r));
    writeUrl({ pair: id });
  }, []);
  const setResult = useCallback((k: ResultKind) => { setResultState(k); writeUrl({ layer: k }); }, []);
  const openTrace = useCallback((tgt: TraceTarget, from: HTMLElement | null) => { opener.current = from; setTrace(tgt); onTraceChange?.(true); }, [onTraceChange]);
  const closeTrace = useCallback(() => {
    setTrace(null);
    onTraceChange?.(false);
    requestAnimationFrame(() => opener.current?.focus());   // focus returns to the value that opened the panel
  }, [onTraceChange]);
  const state = useMemo(() => ({ data, pairId, setPairId, result, setResult, recurrenceGeometry, setRecurrenceGeometry, focus, setFocus, openTrace, file }),
    [data, pairId, setPairId, result, setResult, recurrenceGeometry, focus, openTrace, file]);
  if (data.processing.status === "unavailable") return <Unavailable data={data} />;
  return (
    <CaseContext.Provider value={state}>
      <main id="main" className="layout" inert={trace ? true : undefined}>
        <QuestionSection />
        <SiteSection />
        <aside className="layout__map"><div className="layout__sticky"><MapView /></div></aside>
        <ObservationsSection />
        <QualitySection />
        <NextSection />
        <SourcesSection />
      </main>
      {trace ? <TraceDrawer target={trace} onClose={closeTrace} /> : null}
    </CaseContext.Provider>
  );
}

export default function App() {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const [data, setData] = useState<MiningCase | null>(null);
  const [list, setList] = useState<CaseListItem[]>([]);
  const [error, setError] = useState<LoadError | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [traceOpen, setTraceOpen] = useState(false);
  const i18n = useMemo(() => makeI18n(lang), [lang]);
  const setLang = (l: Lang) => {
    setLangState(l);
    writeUrl({ lang: l });
    try { window.localStorage.setItem("mining.lang", l); } catch { /* not persisted */ }
  };
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.title = `NASA in Mining — ${i18n.t("app.title")}`;
  }, [lang, i18n]);
  useEffect(() => {
    let live = true;
    setError(null);
    const u = readUrl();
    loadCase(u.case, u.run).then(({ data: d, list: l }) => {
      if (!live) return;
      setData(d);
      setList(l);
      writeUrl({ case: d.case_id });
    }).catch((e) => live && setError(e instanceof LoadError ? e : new LoadError("unknown", String(e))));
    return () => { live = false; };
  }, [attempt]);
  return (
    <I18nContext.Provider value={i18n}>
      <Header data={data} list={list} lang={lang} setLang={setLang} inert={traceOpen} />
      {error ? (
        <main id="main" className="error" role="alert">
          <h2>{i18n.t("app.error.title")}</h2>
          <p><code>{error.code}</code> {error.message}</p>
          <p className="muted">{i18n.t("app.error.hint")}</p>
          <button type="button" className="btn" onClick={() => setAttempt((a) => a + 1)}>{i18n.t("app.error.retry")}</button>
        </main>
      ) : !data ? (
        <main id="main" className="loading"><p role="status">{i18n.t("app.loading")}</p></main>
      ) : (
        <CaseView data={data} onTraceChange={setTraceOpen} />
      )}
    </I18nContext.Provider>
  );
}
