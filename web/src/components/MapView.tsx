import { useEffect, useMemo, useRef, useState } from "react";
import type { Layer } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase, type ResultKind } from "../state";
import { Legend } from "./Legend";
import { ZONE_STYLE } from "./zoneStyle";
// The MapLibre 6 worker is a self-contained module; it is shipped as a local asset (works offline).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

type MapLib = typeof import("maplibre-gl");
type MapInstance = import("maplibre-gl").Map;
type Corners = [[number, number], [number, number], [number, number], [number, number]];

export function supportsWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

export function resultLayer(layers: Layer[], pairId: string | null, kind: ResultKind, geometry: string | null): Layer | undefined {
  if (kind === "none") return undefined;
  if (kind === "recurrence" || kind === "observed") {
    const prefix = kind === "recurrence" ? "recurrence_" : "observed_";
    return layers.find((l) => l.id.startsWith(`${prefix}${geometry}_`)) ?? layers.find((l) => l.id.startsWith(prefix));
  }
  return pairId ? layers.find((l) => l.id === `${kind}_${pairId}`) : undefined;
}

type BaseChoice = "before" | "after" | "early" | "late" | "osm";

export function basemapFor(layers: Layer[], pairId: string | null, choice: BaseChoice): Layer | undefined {
  if (choice === "before" || choice === "after") return pairId ? layers.find((l) => l.id === `s2${choice}_${pairId}`) : undefined;
  if (choice === "osm") return undefined;
  return layers.find((l) => l.id === `s2_${choice}`);
}

export function MapView() {
  const { t } = useI18n();
  const { data, pairId, result, setResult, recurrenceGeometry, setRecurrenceGeometry, focus, file } = useCase();
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const [ready, setReady] = useState(false);
  const [webgl] = useState(supportsWebGL);
  const [choice, setChoice] = useState<BaseChoice>("before");
  const [errors, setErrors] = useState<string[]>([]);
  const [snapshot, setSnapshot] = useState<string | null>(null);
  const shown = useMemo(() => resultLayer(data.layers, pairId, result, recurrenceGeometry), [data.layers, pairId, result, recurrenceGeometry]);
  const pair = data.pairs.find((p) => p.pair_id === pairId);
  const hasPairBase = !!(pairId && data.layers.some((l) => l.id === `s2before_${pairId}`));
  const effective: BaseChoice = (choice === "before" || choice === "after") && !hasPairBase ? "late" : choice;
  const base = basemapFor(data.layers, pairId, effective);
  const pairLayers = new Set(data.layers.filter((l) => pairId && l.id.endsWith(pairId)).map((l) => l.id.split("_")[0]));
  const report = (m: string) => setErrors((e) => (e.includes(m) ? e : [...e.slice(-2), m]));

  useEffect(() => {
    if (!webgl || !holder.current) return;
    let cancelled = false;
    import("maplibre-gl").then((lib: MapLib) => {
      if (cancelled || !holder.current) return;
      lib.setWorkerUrl(workerUrl);
      const [lon, lat] = data.site.centroid as [number, number];
      const map = new lib.Map({
        container: holder.current,
        style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#3b4246" } }] },
        center: [lon, lat], zoom: 11.2, attributionControl: false, maxZoom: 16, minZoom: 8,
        canvasContextAttributes: { preserveDrawingBuffer: true },
      });
      map.addControl(new lib.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new lib.ScaleControl({ unit: "metric" }), "bottom-left");
      map.addControl(new lib.AttributionControl({ compact: true, customAttribution: t("print.sources") }));
      const extent = data.layers.find((l) => l.id === "s2_late")?.corners;
      if (extent) map.fitBounds([extent[3] as [number, number], extent[1] as [number, number]], { padding: 8, duration: 0 });
      map.on("error", (e) => report(String((e as { error?: { message?: string } }).error?.message ?? "unknown error")));
      map.on("load", () => {
        holder.current?.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
        mapRef.current = map;
        setReady(true);
      });
    }).catch((e: Error) => report(e.message));
    return () => { cancelled = true; mapRef.current?.remove(); mapRef.current = null; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [webgl, data]);

  // print: a static image of the map as currently shown, next to its legend, dates and sources
  useEffect(() => {
    const capture = () => {
      try { setSnapshot(mapRef.current?.getCanvas().toDataURL("image/png") ?? null); } catch { setSnapshot(null); }
    };
    window.addEventListener("beforeprint", capture);
    return () => window.removeEventListener("beforeprint", capture);
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of ["basemap", "osm"]) {
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    }
    const before = map.getLayer("result") ? "result" : map.getLayer("zones-study_perimeter") ? "zones-control_ring" : undefined;
    if (effective === "osm") {
      map.addSource("osm", { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" });
      map.addLayer({ id: "osm", type: "raster", source: "osm" }, before);
    } else if (base?.corners) {
      map.addSource("basemap", { type: "image", url: file(base.url), coordinates: base.corners as Corners });
      map.addLayer({ id: "basemap", type: "raster", source: "basemap", paint: { "raster-fade-duration": 0, "raster-saturation": -0.35, "raster-brightness-max": 0.92 } }, before);
    }
  }, [ready, effective, base, file]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || map.getSource("zones")) return;
    fetch(file(data.zones_url)).then((r) => { if (!r.ok) throw new Error(`zones: HTTP ${r.status}`); return r.json(); }).then((fc) => {
      if (!mapRef.current || map.getSource("zones")) return;
      map.addSource("zones", { type: "geojson", data: fc });
      for (const [role, st] of Object.entries(ZONE_STYLE)) {
        map.addLayer({ id: `zones-${role}`, type: "line", source: "zones", filter: ["==", ["get", "role"], role],
          paint: { "line-color": st.color, "line-width": st.width, ...(st.dash ? { "line-dasharray": st.dash } : {}) } });
      }
    }).catch((e: Error) => report(e.message));
  }, [ready, data.zones_url, file]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of ["result", "clusters-line"]) if (map.getLayer(id)) map.removeLayer(id);
    for (const id of ["result", "clusters"]) if (map.getSource(id)) map.removeSource(id);
    const before = map.getLayer("zones-study_perimeter") ? "zones-control_ring" : undefined;
    if (shown?.corners) {
      const url = file(shown.url);
      fetch(url, { method: "HEAD" }).then((r) => { if (!r.ok) report(`${t("map.missing")} (${shown.id})`); }).catch(() => report(`${t("map.missing")} (${shown.id})`));
      map.addSource("result", { type: "image", url, coordinates: shown.corners as Corners });
      map.addLayer({ id: "result", type: "raster", source: "result", paint: { "raster-fade-duration": 0, "raster-resampling": "nearest", "raster-opacity": 0.95 } }, before);
    }
    const exp = pairId ? data.exports.find((e) => e.id === `clusters_${pairId}`) : undefined;
    if (exp && result !== "recurrence" && result !== "observed") {
      map.addSource("clusters", { type: "geojson", data: file(exp.path) });
      map.addLayer({ id: "clusters-line", type: "line", source: "clusters", paint: { "line-color": "#ffffff", "line-width": 1.2 } });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, shown, pairId, result, data.exports, file]);

  useEffect(() => {
    if (focus && mapRef.current) mapRef.current.flyTo({ center: focus, zoom: 14, duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 900 });
  }, [focus]);

  const options: { k: ResultKind; label: string; available: boolean }[] = [
    { k: "flags", label: t("layer.flags"), available: pairLayers.has("flags") },
    { k: "coh", label: t("layer.coherence"), available: pairLayers.has("coh") },
    { k: "opt", label: t("layer.optical_change"), available: pairLayers.has("opt") },
    { k: "los", label: t("layer.los"), available: pairLayers.has("los") },
    { k: "recurrence", label: t("layer.recurrence"), available: data.layers.some((l) => l.id.startsWith("recurrence_")) },
    { k: "observed", label: t("layer.observed_count"), available: data.layers.some((l) => l.id.startsWith("observed_")) },
    { k: "none", label: t("map.none"), available: true },
  ];
  const baseOptions: { k: BaseChoice; label: string; layer?: Layer }[] = [
    ...(hasPairBase ? [{ k: "before" as BaseChoice, label: t("map.basemap.before"), layer: basemapFor(data.layers, pairId, "before") },
      { k: "after" as BaseChoice, label: t("map.basemap.after"), layer: basemapFor(data.layers, pairId, "after") }] : []),
    { k: "early", label: t("map.basemap.early"), layer: basemapFor(data.layers, pairId, "early") },
    { k: "late", label: t("map.basemap.late"), layer: basemapFor(data.layers, pairId, "late") },
    { k: "osm", label: t("map.osm") },
  ];
  const baseDate = base?.date_start ?? null;
  const mismatch = pair && baseDate && effective !== "osm" && (baseDate < pair.reference_date || baseDate > pair.secondary_date)
    && !(effective === "before" || effective === "after");
  const geoms = data.geometries.filter((g) => g.recurrence.length);

  return (
    <div className="map">
      <div className="map__canvas" ref={holder} role="region" aria-label={t("map.label")}>
        {!webgl ? <p className="map__fallback">{t("map.webgl")}</p> : null}
      </div>
      <figure className="map__print">
        {snapshot ? <img src={snapshot} alt={t("map.label")} /> : <p>{t("print.nomap")}</p>}
        <figcaption>{t("print.map")} · {shown ? t(shown.title_key) : t("map.none")} · {base ? `${t("map.basemap")} ${base.date_start}` : ""} · {t("print.sources")}</figcaption>
      </figure>
      <div className="map__panel">
        <fieldset className="map__group">
          <legend>{t("map.result")}</legend>
          {options.map((o) => (
            <label key={o.k} className={o.available ? "radio" : "radio radio--off"}>
              <input type="radio" name="result" value={o.k} checked={result === o.k} disabled={!o.available} onChange={() => setResult(o.k)} />
              <span>{o.label}</span>
            </label>
          ))}
          {(result === "recurrence" || result === "observed") && geoms.length ? (
            <label className="select-label">
              <span>{t("site.table.geometry")}</span>
              <select value={recurrenceGeometry ?? ""} onChange={(e) => setRecurrenceGeometry(e.target.value)}>
                {geoms.map((g) => <option key={g.geometry_id} value={g.geometry_id}>{t(`geometry.${g.direction}`)} · T{g.track}</option>)}
              </select>
            </label>
          ) : null}
        </fieldset>
        <fieldset className="map__group">
          <legend>{t("map.basemap")}</legend>
          {baseOptions.filter((o) => o.k === "osm" || o.layer).map((o) => (
            <label key={o.k} className="radio">
              <input type="radio" name="basemap" value={o.k} checked={effective === o.k} onChange={() => setChoice(o.k)} />
              <span>{o.label}{o.layer?.date_start ? ` (${o.layer.date_start})` : ""}</span>
            </label>
          ))}
          {mismatch ? <p className="notice small">{t("map.date_mismatch", { d: baseDate, a: pair!.reference_date, b: pair!.secondary_date })}</p> : null}
        </fieldset>
        <Legend layer={shown} />
        {errors.length ? <div role="alert" className="notice small">{errors.map((e) => <p key={e}>{t("map.error", { m: e })}</p>)}</div> : null}
      </div>
    </div>
  );
}
