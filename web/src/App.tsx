import { useCallback, useEffect, useMemo, useState } from "react";
import { fileUrl, loadCase, LoadError } from "./api";
import type { MiningCase } from "./contract";
import { LANGS, type Lang } from "./i18n";
import { I18nContext, makeI18n, useI18n } from "./i18nContext";
import { CaseContext, type ResultKind, type TraceTarget } from "./state";
import { MapView } from "./components/MapView";
import { NextSection, ObservationsSection, QualitySection, QuestionSection, SiteSection, SourcesSection, STEPS } from "./components/Sections";
import { TraceDrawer } from "./components/TraceDrawer";

function storedLang(): Lang {
  try {
    const v = window.localStorage.getItem("mining.lang");
    if (v === "fr" || v === "en" || v === "ar") return v;
  } catch { /* storage unavailable: default language */ }
  const nav = (navigator.language || "fr").slice(0, 2);
  return (LANGS as string[]).includes(nav) ? (nav as Lang) : "fr";
}

function Header({ data, lang, setLang }: { data: MiningCase | null; lang: Lang; setLang: (l: Lang) => void }) {
  const { t } = useI18n();
  const ok = data?.validation.find((v) => v.observable === "coherence_change_location");
  return (
    <header className="masthead">
      <a className="skip" href="#main">{t("app.skip")}</a>
      <div className="masthead__top">
        <p className="masthead__brand">NASA in Mining</p>
        <div className="masthead__tools">
          <div className="langs" role="group" aria-label={t("app.language")}>
            {LANGS.map((l) => (
              <button key={l} type="button" lang={l} className={l === lang ? "lang is-on" : "lang"} aria-pressed={l === lang} onClick={() => setLang(l)}>{t(`lang.${l}`)}</button>
            ))}
          </div>
          <button type="button" className="btn btn--quiet" onClick={() => window.print()}>{t("app.print")}</button>
        </div>
      </div>
      <h1 className="masthead__title">{t("app.title")}</h1>
      <p className="masthead__tagline">{t("app.tagline")}</p>
      {data ? (
        <ul className="badges" aria-label={t("app.case")}>
          <li className={`badge badge--${data.data_nature}`}>{t(`nature.${data.data_nature}`)}</li>
          <li className={`badge badge--${data.processing.status}`}>{t(`processing.${data.processing.status}`)}</li>
          {ok ? <li className={`badge badge--level-${ok.level}`}>{t(`observable.${ok.observable}`)}{t("punct.colon")}{t(`level.${ok.level}`)}</li> : null}
        </ul>
      ) : null}
      {data ? (
        <nav className="steps" aria-label={t("app.case")}>
          <ol>{STEPS.map((s, i) => <li key={s}><a href={`#step-${s}`}><span aria-hidden="true">{i + 1}</span>{t(`step.${s}`)}</a></li>)}</ol>
        </nav>
      ) : null}
    </header>
  );
}

function Unavailable({ data }: { data: MiningCase }) {
  const { t } = useI18n();
  return (
    <section className="unavailable" aria-labelledby="h-unavail">
      <h2 id="h-unavail">{t("unavailable.title")}</h2>
      <p>{t("unavailable.text")}</p>
      <ul>{data.processing.blockers.map((b) => <li key={b}>{t(b)}</li>)}</ul>
      <ul className="limits">{data.limits.map((k) => <li key={k}>{t(k)}</li>)}</ul>
    </section>
  );
}

export function CaseView({ data }: { data: MiningCase }) {
  const firstOk = data.pairs.find((p) => p.status === "ok")?.pair_id ?? null;
  const preferred = data.findings.find((f) => f.kind === "recurrent_cluster")?.params.pair_id;
  const [pairId, setPairId] = useState<string | null>(typeof preferred === "string" ? preferred : firstOk);
  const [result, setResult] = useState<ResultKind>("flags");
  const [recurrenceGeometry, setRecurrenceGeometry] = useState<string | null>(data.geometries.find((g) => g.recurrence_layer_id)?.geometry_id ?? null);
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const [trace, setTrace] = useState<TraceTarget | null>(null);
  const file = useCallback((path: string) => fileUrl(data.case_id, path), [data.case_id]);
  const selectPair = useCallback((id: string) => { setPairId(id); setResult((r) => (r === "recurrence" || r === "none" ? "flags" : r)); }, []);
  const state = useMemo(() => ({ data, pairId, setPairId: selectPair, result, setResult, recurrenceGeometry, setRecurrenceGeometry, focus, setFocus, openTrace: setTrace, file }),
    [data, pairId, selectPair, result, recurrenceGeometry, focus, file]);
  if (data.processing.status === "unavailable") return <Unavailable data={data} />;
  return (
    <CaseContext.Provider value={state}>
      <main id="main" className="layout">
        <QuestionSection />
        <SiteSection />
        <aside className="layout__map"><div className="layout__sticky"><MapView /></div></aside>
        <ObservationsSection />
        <QualitySection />
        <NextSection />
        <SourcesSection />
      </main>
      {trace ? <TraceDrawer target={trace} onClose={() => setTrace(null)} /> : null}
    </CaseContext.Provider>
  );
}

export default function App() {
  const [lang, setLangState] = useState<Lang>(storedLang);
  const [data, setData] = useState<MiningCase | null>(null);
  const [error, setError] = useState<LoadError | null>(null);
  const [attempt, setAttempt] = useState(0);
  const i18n = useMemo(() => makeI18n(lang), [lang]);
  const setLang = (l: Lang) => {
    setLangState(l);
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
    loadCase().then((c) => live && setData(c)).catch((e) => live && setError(e instanceof LoadError ? e : new LoadError("unknown", String(e))));
    return () => { live = false; };
  }, [attempt]);
  return (
    <I18nContext.Provider value={i18n}>
      <Header data={data} lang={lang} setLang={setLang} />
      {error ? (
        <section className="error" role="alert">
          <h2>{i18n.t("app.error.title")}</h2>
          <p><code>{error.code}</code> {error.message}</p>
          <p className="muted">{i18n.t("app.error.hint")}</p>
          <button type="button" className="btn" onClick={() => setAttempt((a) => a + 1)}>{i18n.t("app.error.retry")}</button>
        </section>
      ) : !data ? (
        <p className="loading" role="status">{i18n.t("app.loading")}</p>
      ) : (
        <CaseView data={data} />
      )}
    </I18nContext.Provider>
  );
}
