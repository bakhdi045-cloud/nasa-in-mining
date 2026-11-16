import { useEffect, useRef, useState } from "react";
import type { Layer } from "../contract";
import { useI18n } from "../i18nContext";
import { Legend } from "../components/Legend";
import { supportsWebGL } from "../components/MapView";
import { ZONE_STYLE } from "../components/zoneStyle";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

type MapLib = typeof import("maplibre-gl");
type MapInstance = import("maplibre-gl").Map;
type Corners = [[number, number], [number, number], [number, number], [number, number]];

interface Props {
  centroid: [number, number];
  zonesUrl: string;
  verificationUrl?: string;
  base?: Layer;
  result?: Layer;
  focus: [number, number] | null;
  file: (path: string) => string;
  resultLabel: string;
}

/** Map of the surface study: Sentinel-2 background of the optical pair, the selected result layer, the outlines. */
export function StudyMap({ centroid, zonesUrl, verificationUrl, base, result, focus, file, resultLabel }: Props) {
  const { t } = useI18n();
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const [ready, setReady] = useState(false);
  const [webgl] = useState(supportsWebGL);
  const [errors, setErrors] = useState<string[]>([]);
  const [snapshot, setSnapshot] = useState<string | null>(null);
  const report = (m: string) => setErrors((e) => (e.includes(m) ? e : [...e.slice(-2), m]));

  useEffect(() => {
    if (!webgl || !holder.current) return;
    let cancelled = false;
    import("maplibre-gl").then((lib: MapLib) => {
      if (cancelled || !holder.current) return;
      lib.setWorkerUrl(workerUrl);
      const map = new lib.Map({
        container: holder.current,
        style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#3b4246" } }] },
        center: centroid, zoom: 11.2, attributionControl: false, maxZoom: 16, minZoom: 8,
        canvasContextAttributes: { preserveDrawingBuffer: true },
      });
      map.addControl(new lib.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new lib.ScaleControl({ unit: "metric" }), "bottom-left");
      map.addControl(new lib.AttributionControl({ compact: true, customAttribution: t("print.sources") }));
      map.on("error", (e) => report(String((e as { error?: { message?: string } }).error?.message ?? "unknown error")));
      map.on("load", () => {
        holder.current?.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
        mapRef.current = map;
        setReady(true);
      });
    }).catch((e: Error) => report(e.message));
    return () => { cancelled = true; mapRef.current?.remove(); mapRef.current = null; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [webgl]);

  useEffect(() => {
    const capture = () => { try { setSnapshot(mapRef.current?.getCanvas().toDataURL("image/png") ?? null); } catch { setSnapshot(null); } };
    window.addEventListener("beforeprint", capture);
    return () => window.removeEventListener("beforeprint", capture);
  }, []);

  // outlines (added once, kept above the rasters)
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || map.getSource("zones")) return;
    fetch(file(zonesUrl)).then((r) => { if (!r.ok) throw new Error(`zones: HTTP ${r.status}`); return r.json(); }).then((fc) => {
      if (!mapRef.current || map.getSource("zones")) return;
      map.addSource("zones", { type: "geojson", data: fc });
      for (const [role, st] of Object.entries(ZONE_STYLE)) {
        map.addLayer({ id: `zones-${role}`, type: "line", source: "zones", filter: ["==", ["get", "role"], role],
          paint: { "line-color": st.color, "line-width": st.width, ...(st.dash ? { "line-dasharray": st.dash } : {}) } });
      }
      if (verificationUrl) {
        map.addSource("vzones", { type: "geojson", data: file(verificationUrl) });
        map.addLayer({ id: "vzones-line", type: "line", source: "vzones", paint: { "line-color": "#c77dff", "line-width": 1.6 } });
      }
    }).catch((e: Error) => report(e.message));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of ["basemap", "result"]) {
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    }
    const above = map.getLayer("zones-study_perimeter") ? "zones-study_perimeter" : undefined;
    if (base?.corners) {
      map.addSource("basemap", { type: "image", url: file(base.url), coordinates: base.corners as Corners });
      map.addLayer({ id: "basemap", type: "raster", source: "basemap", paint: { "raster-fade-duration": 0, "raster-saturation": -0.35, "raster-brightness-max": 0.92 } }, above);
    }
    if (result?.corners) {
      const url = file(result.url);
      fetch(url, { method: "HEAD" }).then((r) => { if (!r.ok) report(`${t("map.missing")} (${result.id})`); }).catch(() => report(`${t("map.missing")} (${result.id})`));
      map.addSource("result", { type: "image", url, coordinates: result.corners as Corners });
      map.addLayer({ id: "result", type: "raster", source: "result", paint: { "raster-fade-duration": 0, "raster-resampling": "nearest", "raster-opacity": 0.95 } }, above);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, base?.id, result?.id, file]);

  useEffect(() => {
    if (focus && mapRef.current) mapRef.current.flyTo({ center: focus, zoom: 14, duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 900 });
  }, [focus]);

  return (
    <div className="map">
      <div className="map__canvas" ref={holder} role="region" aria-label={t("map.label")}>
        {!webgl ? <p className="map__fallback">{t("map.webgl")}</p> : null}
      </div>
      <figure className="map__print">
        {snapshot ? <img src={snapshot} alt={t("map.label")} /> : <p>{t("print.nomap")}</p>}
        <figcaption>{t("print.map")} · {resultLabel} · {base ? `${t("map.basemap")} ${base.date_start}` : ""} · {t("print.sources")}</figcaption>
      </figure>
      <div className="map__panel">
        <Legend layer={result} />
        {errors.length ? <div role="alert" className="notice small">{errors.map((e) => <p key={e}>{t("map.error", { m: e })}</p>)}</div> : null}
      </div>
    </div>
  );
}
