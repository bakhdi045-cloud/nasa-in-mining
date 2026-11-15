"""Build cases/benguerir/zones.geojson from recorded OpenStreetMap extracts (ODbL).

Inputs (git-ignored, recorded by their Overpass timestamp): data/sources/osm/quarry.json and context.json.
Refetch them with --fetch (public Overpass API, no credential). Output is small and committed with attribution.

Run: python scripts/build_benguerir_zones.py [--fetch]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shapely.geometry import mapping, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from nasa_in_mining.mining import zones  # noqa: E402

STUDY_WAY = 638354631
EPSG = 32629
RING_INNER_M, RING_OUTER_M, EXCLUSION_BUFFER_M = 1000.0, 4000.0, 100.0
SRC = ROOT / "data" / "sources" / "osm"
OUT = ROOT / "cases" / "benguerir" / "zones.geojson"
QUERIES = {
    "quarry.json": "[out:json][timeout:60];(way[landuse=quarry](32.15,-8.0,32.40,-7.65);"
                   "relation[landuse=quarry](32.15,-8.0,32.40,-7.65););out meta geom;",
    "context.json": '[out:json][timeout:120];(way[landuse~"residential|industrial|commercial|construction|retail|'
                    'railway|landfill|brownfield|military"](32.13,-7.95,32.38,-7.70);relation[landuse~"residential|'
                    'industrial|commercial|construction"](32.13,-7.95,32.38,-7.70);way[amenity=university]'
                    '(32.13,-7.95,32.38,-7.70);way[aeroway=aerodrome](32.13,-7.95,32.38,-7.70);way[man_made~'
                    '"wastewater_plant|works|tailings_pond|spoil_heap"](32.13,-7.95,32.38,-7.70);way[natural=water]'
                    '(32.13,-7.95,32.38,-7.70);way[landuse=quarry](32.0,-8.1,32.5,-7.5););out meta geom;',
}


def fetch() -> None:
    import requests
    SRC.mkdir(parents=True, exist_ok=True)
    for name, query in QUERIES.items():
        for attempt in range(6):
            r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query},
                              headers={"User-Agent": "nasa-in-mining/0.2 (research)"}, timeout=180)
            if r.ok and r.content.startswith(b"{"):
                (SRC / name).write_bytes(r.content)
                break
            time.sleep(30)
        else:
            raise SystemExit(f"Overpass did not answer for {name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="refetch the OSM extracts from Overpass")
    args = ap.parse_args()
    if args.fetch:
        fetch()
    quarry = json.loads((SRC / "quarry.json").read_text(encoding="utf-8"))
    context = json.loads((SRC / "context.json").read_text(encoding="utf-8"))
    way = next(e for e in quarry["elements"] if e["type"] == "way" and e["id"] == STUDY_WAY)
    study = zones.osm_way_polygon(way)
    excl = zones.exclusion_features(context, STUDY_WAY)
    panels = [shape(f["geometry"]) for f in excl if f["properties"]["osm_type"] == "relation"
              and f["properties"]["class"] == "industrial"]
    panels_outside = unary_union(panels).difference(study) if panels else None
    others = [shape(f["geometry"]) for f in excl]
    ring, ring_km2 = zones.control_ring(study, others, EPSG, RING_INNER_M, RING_OUTER_M, EXCLUSION_BUFFER_M)
    base = {"osm_base_timestamp": quarry["osm3s"]["timestamp_osm_base"], "license": "ODbL-1.0",
            "attribution": "© OpenStreetMap contributors"}
    features = [
        {"type": "Feature", "id": "study", "geometry": mapping(study), "properties": {
            **base, "role": "study_perimeter", "label": "Zone de carrière cartographiée (OSM landuse=quarry)",
            "osm_type": "way", "osm_id": STUDY_WAY, "osm_version": way.get("version"),
            "osm_timestamp": way.get("timestamp"), "area_km2": round(zones.area_km2(study, EPSG), 3),
            "nature": "mapped extent of quarry land use; not a mining concession or legal boundary"}},
        {"type": "Feature", "id": "control", "geometry": mapping(ring), "properties": {
            **base, "role": "control_ring", "label": "Anneau témoin 1–4 km hors carrière, zones bâties exclues",
            "inner_m": RING_INNER_M, "outer_m": RING_OUTER_M, "exclusion_buffer_m": EXCLUSION_BUFFER_M,
            "area_km2": round(ring_km2, 3),
            "nature": "geometric construction; surrounding land observed by the same acquisitions, not proven stable"}},
    ]
    if panels_outside is not None and not panels_outside.is_empty:
        features.append({"type": "Feature", "id": "panels_outside", "geometry": mapping(panels_outside),
                         "properties": {**base, "role": "mapped_mining_outside_perimeter",
                                        "label": "Parcelles minières OSM (2020) hors du polygone de carrière",
                                        "n_relations": len(panels),
                                        "area_km2": round(zones.area_km2(panels_outside, EPSG), 3),
                                        "nature": "OSM multipolygons landuse=industrial named P1S/P2/P4/P5/P7..., "
                                                  "changeset source=knowledge (2020); semantics not confirmed"}})
    excluded = unary_union(others)
    features.append({"type": "Feature", "id": "exclusions", "geometry": mapping(excluded.simplify(0.00001)),
                     "properties": {**base, "role": "exclusion", "n_features": len(excl),
                                    "label": "Zones cartographiées exclues du témoin (bâti, industrie, base, etc.)"}})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({f["id"]: f["properties"].get("area_km2") for f in features}, ensure_ascii=False))


if __name__ == "__main__":
    main()
