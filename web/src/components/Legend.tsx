import type { Layer } from "../contract";
import { useI18n } from "../i18nContext";
import { ZONE_STYLE } from "./zoneStyle";

const rgb = (c: number[]) => `rgb(${c[0]} ${c[1]} ${c[2]} / ${(c[3] ?? 255) / 255})`;

export function Legend({ layer }: { layer?: Layer }) {
  const { t, f } = useI18n();
  const lg = layer?.legend;
  return (
    <div className="legend" role="group" aria-label={t("map.legend")}>
      <p className="legend__title">{t("map.legend")}</p>
      <ul className="legend__zones">
        {Object.entries(ZONE_STYLE).map(([role, st]) => (
          <li key={role}>
            <svg width="26" height="10" aria-hidden="true"><line x1="1" y1="5" x2="25" y2="5" stroke={st.color} strokeWidth={st.width + 0.6} strokeDasharray={st.dash ? "4 3" : undefined} /></svg>
            {t(st.key)}
          </li>
        ))}
      </ul>
      {layer && lg ? (
        <div className="legend__layer">
          <p className="legend__name">{t(layer.title_key)}</p>
          {lg.kind === "continuous" && lg.stops ? (
            <>
              <div className="legend__ramp" style={{ background: `linear-gradient(to right, ${lg.stops.join(", ")})` }} />
              <div className="legend__ticks"><span>{f.num(lg.vmin ?? null, 2)}</span><span>{lg.unit}</span><span>{f.num(lg.vmax ?? null, 2)}</span></div>
            </>
          ) : null}
          {lg.kind === "categorical" && lg.classes ? (
            <ul className="legend__classes">
              {Object.entries(lg.classes).map(([k, c]) => (
                <li key={k}><span className="swatch" style={{ background: rgb(c as number[]) }} />{t(lg.class_keys?.[k] ?? k)}</li>
              ))}
            </ul>
          ) : null}
          <p className="legend__meta">
            {layer.date_start ? t("map.dates", { a: layer.date_start, b: layer.date_end ?? layer.date_start }) : null}
            {layer.resolution_m ? ` · ${t("map.resolution", { r: layer.resolution_m })}` : null}
          </p>
          {layer.display_note_key ? <p className="legend__meta">{t(layer.display_note_key)}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
