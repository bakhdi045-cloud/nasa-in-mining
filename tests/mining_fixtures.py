"""SYNTHETIC mining-case fixtures (test data only, never presented as observations).

A 6 x 6 km UTM 29N window at 20 m (coherence, mask) and 80 m (phase, coherence, components). The study perimeter is a
2 x 2 km square in the centre; the control ring lies between 500 m and 2 km from it. Background coherence is a
constant 0.8, so the control 1 % quantile equals 0.8 and only pixels set lower are flagged: expected areas are exact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import box, mapping
from shapely.ops import transform

from tests import support as s

EPSG = 32629
X0, Y0 = 600000.0, 3570000.0          # upper-left corner of the window
SIZE_M = 6000.0
N20, N80 = 300, 75
CHANGE_ROWS, CHANGE_COLS = slice(120, 145), slice(120, 145)     # 25 x 25 px = 0.25 km2, inside the study square
NODATA_ROWS, NODATA_COLS = slice(160, 170), slice(160, 170)     # 10 x 10 px not observed inside the study square
CHANGE_KM2 = 25 * 25 * 0.0004
STUDY_PIXELS = 100 * 100
DATES = [("20260101", "20260113"), ("20260113", "20260125"), ("20260125", "20260206")]

to_ll = Transformer.from_crs(EPSG, 4326, always_xy=True).transform


def _zones() -> dict:
    study_m = box(X0 + 2000, Y0 - 4000, X0 + 4000, Y0 - 2000)
    ring_m = study_m.buffer(2000).difference(study_m.buffer(500)).intersection(box(X0, Y0 - SIZE_M, X0 + SIZE_M, Y0))
    base = {"license": "test", "attribution": "synthetic", "osm_base_timestamp": "2026-01-01T00:00:00Z"}
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "study", "geometry": mapping(transform(to_ll, study_m)),
         "properties": {**base, "role": "study_perimeter", "area_km2": 4.0, "osm_type": "synthetic", "osm_id": 0}},
        {"type": "Feature", "id": "control", "geometry": mapping(transform(to_ll, ring_m)),
         "properties": {**base, "role": "control_ring", "area_km2": round(ring_m.area / 1e6, 3)}},
    ]}


def write_case(case_dir: Path) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    real = json.loads((Path(__file__).resolve().parents[1] / "cases" / "benguerir" / "case_config.json").read_text(encoding="utf-8"))
    real.update(case_id="synthetic-test", data_nature="synthetic",
                site={**real["site"], "id": "synthetic", "name": "SYNTHETIC test site"})
    (case_dir / "case_config.json").write_text(json.dumps(real), encoding="utf-8")
    (case_dir / "zones.geojson").write_text(json.dumps(_zones()), encoding="utf-8")
    return case_dir


def _product(data: Path, a: str, b: str, coh20: np.ndarray, mask20: np.ndarray, flat: bool = False,
             shape20: tuple | None = None) -> Path:
    folder = s.product_dir(data, "GUNW", a, b)
    t20, t80 = from_origin(X0, Y0, 20, 20), from_origin(X0, Y0, 80, 80)
    rng = np.random.default_rng(int(a))
    if shape20:
        coh20 = np.full(shape20, 0.8, "float32")
        mask20 = np.full(shape20, 11, "uint32")
    s.write_tif(folder / "wrappedInterferogram_HH_coherenceMagnitude.tif", coh20.astype("float32"), t20, f"EPSG:{EPSG}")
    s.write_tif(folder / "wrappedInterferogram_mask.tif", mask20.astype("uint32"), t20, f"EPSG:{EPSG}")
    phase = np.zeros((N80, N80), "float32") if flat else rng.normal(0, 0.5, (N80, N80)).astype("float32")
    s.write_tif(folder / "unwrappedInterferogram_HH_unwrappedPhase.tif", phase, t80, f"EPSG:{EPSG}")
    s.write_tif(folder / "unwrappedInterferogram_HH_coherenceMagnitude.tif", np.full((N80, N80), 0.8, "float32"), t80, f"EPSG:{EPSG}")
    s.write_tif(folder / "unwrappedInterferogram_HH_connectedComponents.tif", np.ones((N80, N80), "uint16"), t80, f"EPSG:{EPSG}")
    np.savez_compressed(folder / "radar_geometry.npz", centerFrequency=s.FREQ)
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()  # noqa: E731
    mask_desc = ("SYNTHETIC. Bits 0-7 represent subswath encoding (water, reference, secondary digits). "
                 "Bits 8-15 represent bitwise anomaly flags for the secondary RSLC.")
    files = {f.name: {"sha256": sha(f), "spacing_m": [20.0, -20.0], "units": "1",
                      "description": mask_desc if "mask" in f.name else "synthetic"} for f in folder.glob("*.tif")}
    (folder / "provenance.json").write_text(json.dumps({
        "granule_id": folder.name, "source_url": f"https://example.invalid/SYNTHETIC/{folder.name}.h5",
        "layers": files, "identification": {"productVersion": "synthetic", "referenceZeroDopplerStartTime": f"{a[:4]}-{a[4:6]}-{a[6:]}T05:38:52",
                                             "secondaryZeroDopplerStartTime": f"{b[:4]}-{b[4:6]}-{b[6:]}T05:38:52"},
        "processing": {"wrapped_azimuth_looks": 6, "wrapped_range_looks": 5}, "bytes_transferred": 0,
        "files": {**{k: v["sha256"] for k, v in files.items()}, "radar_geometry.npz": sha(folder / "radar_geometry.npz")}}),
        encoding="utf-8")
    (folder / "_DONE").write_text("{}", encoding="utf-8")
    return folder


def write_data(data: Path, incompatible: bool = False, rejected: bool = False, flat_phase_only: bool = False) -> Path:
    if data.exists():
        shutil.rmtree(data)
    for i, (a, b) in enumerate(DATES):
        coh = np.full((N20, N20), 0.8, "float32")
        mask = np.full((N20, N20), 11, "uint32")
        if i == 1:
            coh[CHANGE_ROWS, CHANGE_COLS] = 0.05          # real change in one pair only
        if i == 2:
            coh[CHANGE_ROWS, CHANGE_COLS] = 0.0           # a measured zero coherence, not missing data
        coh[NODATA_ROWS, NODATA_COLS] = np.nan            # not observed in every pair
        if rejected and i == 0:
            coh[:] = 0.01                                  # a defective product: near-zero coherence everywhere
        _product(data, a, b, coh, mask, flat=(rejected or flat_phase_only) and i == 0,
                 shape20=(N20 + 5, N20) if incompatible and i == 2 else None)
    return data
