import { createContext, useContext } from "react";
import type { Params } from "./contract";
import { makeFmt, translate, type Fmt, type Lang } from "./i18n";

export interface I18n {
  lang: Lang;
  t: (key: string, params?: Params) => string;
  f: Fmt;
}

export const I18nContext = createContext<I18n>({ lang: "fr", t: (k, p) => translate("fr", k, p), f: makeFmt("fr") });
export const useI18n = () => useContext(I18nContext);

export function makeI18n(lang: Lang): I18n {
  return { lang, t: (k, p) => translate(lang, k, p), f: makeFmt(lang) };
}
