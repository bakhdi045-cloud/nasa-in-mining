import { useEffect, useMemo, useRef, useState } from "react";
import type { Layer } from "../contract";
import { useI18n } from "../i18nContext";
import { useCase, type ResultKind } from "../state";
import { Legend } from "./Legend";
import { ZONE_STYLE } from "./zoneStyle";

// The MapLibre 6 worker is a self-contained module; ship it as a local asset (works offline).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

type MapLib = typeof import("maplibre-gl");
type MapInstance = import("maplibre-gl").Map;

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
  if (kind === "recurrence") return layers.find((l) => l.id === `recurrence_${geometry}`) ?? layers.find((l) => l.id.startsWith("recurrence_"));
  return pairId ? layers.find((l) => l.id === `${kind}_${pairId}`) : undefined;
}

export function MapView() {
  const { t } = useI18n();
  const { data, pairId, result, setResult, recurrenceGeometry, setRecurrenceGeometry, focus, file } = useCase();
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const libRef = useRef<MapLib | null>(null);
  const [ready, setReady] = useState(false);
  const [webgl] = useState(supportsWebGL);
  const [basemap, setBasemap] = useState<"s2_late" | "s2_early" | "osm">("s2_late");
  const [missing, setMissing] = useState<string | null>(null);
  const shown = useMemo(() => resultLayer(data.layers, pairId, result, recurrenceGeometry), [data.layers, pairId, result, recurrenceGeometry]);
  const base = data.layers.find((l) => l.id === basemap);
  const pairLayers = new Set(data.layers.filter((l) => pairId && l.id.endsWith(pairId)).map((l) => l.id.split("_")[0]));

  // create the map once
  useEffect(() => {
    if (!webgl || !holder.current) return;
    let cancelled = false;
    import("maplibre-gl").then((lib) => {
      if (cancelled || !holder.current) return;
      libRef.current = lib;
      lib.setWorkerUrl(workerUrl);
      const [lon, lat] = data.site.centroid;
      const map = new lib.Map({
        container: holder.current,
        style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#3b4246" } }] },
        center: [lon, lat], zoom: 11.2, attributionControl: false, maxZoom: 16, minZoom: 8,
      });
      map.addControl(new lib.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new lib.ScaleControl({ unit: "metric" }), "bottom-left");
      map.addControl(new lib.AttributionControl({ compact: true, customAttribution: "Sentinel-2: Contains modified Copernicus Sentinel data 2026 · Zones: © OpenStreetMap contributors (ODbL) · NISAR: NASA/JPL, ASF DAAC" }));
      const study = data.layers.find((l) => l.id === "s2_late")?.corners;
      if (study) map.fitBounds([study[3] as [number, number], study[1] as [number, number]], { padding: 8, duration: 0 });
      map.on("load", () => {
        holder.current?.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
        mapRef.current = map;
        setReady(true);
      });
    }).catch(() => undefined);
    return () => { cancelled = true; mapRef.current?.remove(); mapRef.current = null; };
  }, [webgl, data.site.centroid, data.layers]);

  // basemap
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of ["basemap", "osm"]) {
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    }
    const before = map.getLayer("result") ? "result" : map.getLayer("zones-study_perimeter") ? "zones-control_ring" : undefined;
    if (basemap === "osm") {
      map.addSource("osm", { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" });
      map.addLayer({ id: "osm", type: "raster", source: "osm" }, before);
    } else if (base?.corners) {
      map.addSource("basemap", { type: "image", url: file(base.url), coordinates: base.corners as [[number, number], [number, number], [number, number], [number, number]] });
      map.addLayer({ id: "basemap", type: "raster", source: "basemap", paint: { "raster-fade-duration": 0, "raster-saturation": -0.35, "raster-brightness-max": 0.92 } }, before);
    }
  }, [ready, basemap, base, file]);

  // zones and their legend outlines
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || map.getSource("zones")) return;
    fetch(file(data.zones_url)).then((r) => r.json()).then((fc) => {
      if (!mapRef.current || map.getSource("zones")) return;
      map.addSource("zones", { type: "geojson", data: fc });
      for (const [id, st] of Object.entries(ZONE_STYLE)) {
        map.addLayer({ id: `zones-${id}`, type: "line", source: "zones", filter: ["==", ["get", "role"], id],
          paint: { "line-color": st.color, "line-width": st.width, ...(st.dash ? { "line-dasharray": st.dash } : {}) } });
      }
    }).catch(() => undefined);
  }, [ready, data.zones_url, file]);

  // result overlay + clusters
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of ["result", "clusters-line"]) if (map.getLayer(id)) map.removeLayer(id);
    for (const id of ["result", "clusters"]) if (map.getSource(id)) map.removeSource(id);
    setMissing(null);
    const before = map.getLayer("zones-study_perimeter") ? "zones-control_ring" : undefined;
    if (shown?.corners) {
      const url = file(shown.url);
      fetch(url, { method: "HEAD" }).then((r) => { if (!r.ok) setMissing(shown.id); }).catch(() => setMissing(shown.id));
      map.addSource("result", { type: "image", url, coordinates: shown.corners as [[number, number], [number, number], [number, number], [number, number]] });
      map.addLayer({ id: "result", type: "raster", source: "result", paint: { "raster-fade-duration": 0, "raster-resampling": "nearest", "raster-opacity": 0.95 } }, before);
    }
    const exp = pairId ? data.exports.find((e) => e.id === `clusters_${pairId}`) : undefined;
    if (exp && result !== "recurrence") {
      map.addSource("clusters", { type: "geojson", data: file(exp.path) });
      map.addLayer({ id: "clusters-line", type: "line", source: "clusters", paint: { "line-color": "#ffffff", "line-width": 1.2 } });
    }
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
    { k: "none", label: t("map.none"), available: true },
  ];

  return (
    <div className="map">
      <div className="map__canvas" ref={holder} role="region" aria-label={t("map.label")}>
        {!webgl ? <p className="map__fallback">{t("map.webgl")}</p> : null}
      </div>
      <div className="map__panel">
        <fieldset className="map__group">
          <legend>{t("map.result")}</legend>
          {options.map((o) => (
            <label key={o.k} className={o.available ? "radio" : "radio radio--off"}>
              <input type="radio" name="result" value={o.k} checked={result === o.k} disabled={!o.available} onChange={() => setResult(o.k)} />
              <span>{o.label}</span>
            </label>
          ))}
          {result === "recurrence" ? (
            <select aria-label={t("site.table.geometry")} value={recurrenceGeometry ?? ""} onChange={(e) => setRecurrenceGeometry(e.target.value)}>
              {data.geometries.filter((g) => g.recurrence_layer_id).map((g) => (
                <option key={g.geometry_id} value={g.geometry_id}>{t(`geometry.${g.direction}`)} · T{g.track}</option>
              ))}
            </select>
          ) : null}
        </fieldset>
        <fieldset className="map__group">
          <legend>{t("map.basemap")}</legend>
          {(["s2_late", "s2_early", "osm"] as const).map((b) => {
            const l = data.layers.find((x) => x.id === b);
            if (b !== "osm" && !l) return null;
            return (
              <label key={b} className="radio">
                <input type="radio" name="basemap" value={b} checked={basemap === b} onChange={() => setBasemap(b)} />
                <span>{b === "osm" ? t("map.osm") : `${t(b === "s2_late" ? "map.basemap.late" : "map.basemap.early")} (${l?.date_start})`}</span>
              </label>
            );
          })}
        </fieldset>
        <Legend layer={shown} />
        {missing ? <p className="notice">{t("map.missing")}</p> : null}
      </div>
    </div>
  );
}
