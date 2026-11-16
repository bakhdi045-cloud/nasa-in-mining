"""Crop NISAR L2 GCOV layers to an area of interest over HTTP range reads (new, surface study).

GCOV gives calibrated, terrain-normalised backscatter on a map grid. Layers copied (frequency A, no resampling):
HHHH and HVHV (gamma-0, linear power), `mask` (subswath number of valid samples, 0 = not fully focused, 255 =
outside the acquisition), `numberOfLooks` and `inputDataExceptionMask` (bit 1 = LSAR qFSP-H1 sample slip).
Also copied at their native coarse grids: the noise-equivalent backscatter (HH, HV; linear power) and the
incidence angle (mean over the height axis). Nothing is inferred: a property that the product does not state
stays absent from the provenance.

The window is aligned on the 20 m analysis grid (the native grid is 10 m): its edges are multiples of 20 m, so
that a 2 x 2 block mean in linear power reproduces the 20 m grid of the GUNW crops exactly.

Layout:  <data>/GCOV/<granule>/_DONE, provenance.json, *.tif
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil

import h5py
import numpy as np
import rasterio
from rasterio.transform import from_origin

from .nisar_subset import _attr, _scalar, _sha256
from .remote import RangeFile

G = "science/LSAR/GCOV"
GRID = f"{G}/grids/frequencyA"
META = f"{G}/metadata"
EXTRACTOR_VERSION = "1"
ANALYSIS_M = 20.0
FINE = {  # output file: dataset under GRID
    "HHHH.tif": "HHHH", "HVHV.tif": "HVHV", "mask.tif": "mask", "numberOfLooks.tif": "numberOfLooks",
    "inputDataExceptionMask.tif": "inputDataExceptionMask"}
IDENT = ["productVersion", "productSpecificationVersion", "compositeReleaseId", "processingDateTime", "productDoi",
         "orbitPassDirection", "lookDirection", "trackNumber", "frameNumber", "absoluteOrbitNumber",
         "zeroDopplerStartTime", "zeroDopplerEndTime", "isFullFrame", "processingType", "granuleId",
         "diagnosticModeFlag", "hasInputDataException", "isMixedMode", "isDithered", "isUrgentObservation",
         "listOfObservationModes", "plannedObservationId", "plannedDatatakeId", "radarBand", "listOfFrequencies"]
PARAMS = {  # booleans/strings stated by the product; absent stays None
    "noise_correction_applied": "parameters/noiseCorrectionApplied",
    "rtc_applied": "parameters/radiometricTerrainCorrectionApplied",
    "rfi_mitigation_applied": "parameters/rfiMitigationApplied",
    "faraday_rotation_applied": "parameters/faradayRotationApplied",
    "post_processing_filtering_applied": "parameters/postProcessingFilteringApplied",
    "polarimetric_symmetrization_applied": "parameters/polarimetricSymmetrizationApplied",
    "is_full_covariance": "parameters/isFullCovariance",
    "normalization": "parameters/rtc/outputBackscatterNormalizationConvention",
    "expression": "parameters/rtc/outputBackscatterExpressionConvention",
    "min_rtc_area_factor_db": "parameters/rtc/minRtcAreaNormalizationFactorInDB",
    "software_version": "algorithms/softwareVersion",
    "geocoding": "algorithms/geocoding",
    "rtc_algorithm": "algorithms/radiometricTerrainCorrection",
    "dem_source": "inputs/demSource",
}


class GcovError(RuntimeError):
    pass


def aligned_window(x: np.ndarray, y: np.ndarray, aoi: tuple[float, float, float, float], spacing: float = 10.0,
                   block: float = ANALYSIS_M):
    """Row/column slices of the pixels whose centres lie in aoi, trimmed so that the window edges are multiples
    of `block` metres and its size is a whole number of blocks."""
    xmin, ymin, xmax, ymax = aoi
    cols = np.nonzero((x >= xmin) & (x <= xmax))[0]
    rows = np.nonzero((y >= ymin) & (y <= ymax))[0]
    if cols.size == 0 or rows.size == 0:
        return None
    c0, c1 = int(cols[0]), int(cols[-1]) + 1
    r0, r1 = int(rows[0]), int(rows[-1]) + 1
    k = int(round(block / spacing))
    while c0 < c1 and (x[c0] - spacing / 2) % block > 1e-6 and block - (x[c0] - spacing / 2) % block > 1e-6:
        c0 += 1
    while r0 < r1 and (y[r0] + spacing / 2) % block > 1e-6 and block - (y[r0] + spacing / 2) % block > 1e-6:
        r0 += 1
    c1 = c0 + ((c1 - c0) // k) * k
    r1 = r0 + ((r1 - r0) // k) * k
    if c1 <= c0 or r1 <= r0:
        return None
    return slice(r0, r1), slice(c0, c1)


def cache_key(granule_id: str, aoi_utm, epsg: int) -> dict:
    return {"granule_id": granule_id, "aoi_utm": [float(v) for v in aoi_utm], "epsg": int(epsg),
            "layers": FINE, "extractor_version": EXTRACTOR_VERSION}


def verify(folder: Path, key: dict | None = None) -> tuple[bool, str]:
    prov = folder / "provenance.json"
    if not (folder / "_DONE").exists() or not prov.exists():
        return False, "incomplete crop (no _DONE or provenance)"
    try:
        rec = json.loads(prov.read_text(encoding="utf-8"))
    except ValueError:
        return False, "unreadable provenance"
    if key is not None and rec.get("cache_key") != key:
        return False, "crop made with other parameters"
    if not rec.get("files"):
        return False, "provenance without file fingerprints"
    for name, digest in rec["files"].items():
        f = folder / name
        if not f.exists():
            return False, f"missing file {name}"
        if _sha256(f) != digest:
            return False, f"file {name} differs from its recorded fingerprint"
    return True, ""


def _write(path: Path, arr: np.ndarray, transform, epsg: int, nodata, **tags) -> None:
    with rasterio.open(path, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1, dtype=arr.dtype,
                       crs=f"EPSG:{epsg}", transform=transform, nodata=nodata, compress="deflate") as dst:
        dst.write(arr, 1)
        dst.update_tags(**{k: str(v) for k, v in tags.items()})


def _coarse(h5, ds_path: str, grp_path: str, aoi, margin: float):
    """Crop a coarse-grid dataset (own x/y coordinates) to aoi + margin; returns (array, transform, spacing)."""
    grp = h5[grp_path]
    x, y = grp["xCoordinates"][()], grp["yCoordinates"][()]
    dx, dy = abs(float(x[1] - x[0])), abs(float(y[1] - y[0]))
    xmin, ymin, xmax, ymax = aoi
    cols = np.nonzero((x >= xmin - margin) & (x <= xmax + margin))[0]
    rows = np.nonzero((y >= ymin - margin) & (y <= ymax + margin))[0]
    if cols.size == 0 or rows.size == 0:
        return None
    win = (slice(int(rows[0]), int(rows[-1]) + 1), slice(int(cols[0]), int(cols[-1]) + 1))
    ds = h5[ds_path]
    arr = ds[(slice(None),) + win] if ds.ndim == 3 else ds[win]
    if arr.ndim == 3:
        arr = np.nanmean(arr, axis=0)
    transform = from_origin(float(x[win[1].start]) - dx / 2, float(y[win[0].start]) + dy / 2, dx, dy)
    return arr.astype("float32"), transform, (dx, dy)


def extract(url: str, granule_id: str, out_root: Path, aoi_utm: tuple[float, float, float, float],
            epsg_expected: int = 32629, overwrite: bool = False) -> dict:
    """Crop one GCOV granule into a temporary folder, verify it, then publish it atomically."""
    folder = Path(out_root) / "GCOV" / granule_id
    key = cache_key(granule_id, aoi_utm, epsg_expected)
    if not overwrite:
        ok, _ = verify(folder, key)
        if ok:
            return json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    tmp = folder.with_name(folder.name + ".partial")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    rf = RangeFile(url)
    record: dict = {"granule_id": granule_id, "source_url": url, "source_size_bytes": rf.size, "aoi_utm": list(aoi_utm),
                    "epsg": None, "layers": {}, "identification": {}, "processing": {}, "calibration": {},
                    "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "method": "HTTP range read of the original HDF5, frequency A; no resampling; crop aligned on the "
                              "20 m analysis grid", "cache_key": key}
    with h5py.File(rf, "r") as h5:
        ident = h5["science/LSAR/identification"]
        record["identification"] = {k: _scalar(ident[k]) for k in IDENT if k in ident}
        for k, rel in PARAMS.items():
            full = f"{META}/processingInformation/{rel}"
            record["processing"][k] = _scalar(h5[full]) if full in h5 else None
        g = h5[GRID]
        epsg = int(g["projection"][()])
        if epsg != epsg_expected:
            raise GcovError(f"{granule_id}: grid EPSG {epsg} differs from the expected {epsg_expected}")
        record["epsg"] = epsg
        record["center_frequency_hz"] = float(g["centerFrequency"][()]) if "centerFrequency" in g else None
        pols = [p.decode() if isinstance(p, bytes) else str(p) for p in g["listOfPolarizations"][()]]
        record["polarizations"] = pols
        record["n_subswaths"] = int(g["numberOfSubSwaths"][()])
        x, y = g["xCoordinates"][()], g["yCoordinates"][()]
        dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
        record["native_spacing_m"] = [dx, dy]
        win = aligned_window(x, y, aoi_utm, spacing=abs(dx))
        if win is None:
            raise GcovError(f"{granule_id}: the AOI is outside the GCOV grid")
        transform = from_origin(float(x[win[1].start]) - dx / 2, float(y[win[0].start]) + abs(dy) / 2, dx, abs(dy))
        for fname, rel in FINE.items():
            if rel in ("HHHH", "HVHV") and rel[:2] not in pols:
                continue
            ds = g[rel]
            arr = ds[win]
            fill = ds.attrs.get("_FillValue")
            fill = None if fill is None else float(fill)
            nodata = np.nan if arr.dtype.kind == "f" else (None if fill is None or not math.isfinite(fill) else fill)
            path = tmp / fname
            _write(path, arr, transform, epsg, nodata, source_dataset=f"{GRID}/{rel}", granule=granule_id,
                   units=_attr(ds, "units"))
            record["layers"][fname] = {
                "dataset": f"{GRID}/{rel}", "spacing_m": [dx, abs(dy)], "shape": list(arr.shape),
                "rows": [win[0].start, win[0].stop], "cols": [win[1].start, win[1].stop], "units": _attr(ds, "units"),
                "description": _attr(ds, "description"), "fill_value": fill if fill is None or math.isfinite(fill) else "NaN",
                "sha256": _sha256(path)}
        aoi_box = (float(x[win[1].start]), float(y[win[0].stop - 1]), float(x[win[1].stop - 1]), float(y[win[0].start]))
        cal = f"{META}/calibrationInformation/frequencyA/noiseEquivalentBackscatter"
        for pol in pols:
            if f"{cal}/{pol}" in h5:
                res = _coarse(h5, f"{cal}/{pol}", cal, aoi_box, margin=2000.0)
                if res is not None:
                    arr, tr, sp = res
                    name = f"noiseEquivalentBackscatter_{pol}.tif"
                    _write(tmp / name, arr, tr, epsg, np.nan, units="linear power (DN^2)",
                           source_dataset=f"{cal}/{pol}")
                    record["layers"][name] = {"dataset": f"{cal}/{pol}", "spacing_m": list(sp), "shape": list(arr.shape),
                                              "units": "linear power (DN^2)", "description": "noise equivalent backscatter",
                                              "sha256": _sha256(tmp / name)}
        ia = f"{META}/radarGrid/incidenceAngle"
        if ia in h5:
            res = _coarse(h5, ia, f"{META}/radarGrid", aoi_box, margin=2000.0)
            if res is not None:
                arr, tr, sp = res
                _write(tmp / "incidenceAngle.tif", arr, tr, epsg, np.nan, units=_attr(h5[ia], "units"),
                       aggregation="mean over the height axis")
                record["layers"]["incidenceAngle.tif"] = {
                    "dataset": ia, "spacing_m": list(sp), "shape": list(arr.shape), "units": _attr(h5[ia], "units"),
                    "description": "incidence angle, mean over the height axis", "sha256": _sha256(tmp / "incidenceAngle.tif")}
    record["bytes_transferred"] = rf.bytes_read
    record["range_requests"] = rf.requests
    record["files"] = {k: v["sha256"] for k, v in record["layers"].items()}
    (tmp / "provenance.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8", newline="\n")
    (tmp / "_DONE").write_text(json.dumps({"provenance": "provenance.json"}), encoding="utf-8")
    ok, why = verify(tmp, key)
    if not ok:
        raise GcovError(f"{granule_id}: crop failed verification ({why})")
    shutil.rmtree(folder, ignore_errors=True)
    os.replace(tmp, folder)
    return record
