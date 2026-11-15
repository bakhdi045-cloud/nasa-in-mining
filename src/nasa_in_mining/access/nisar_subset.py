"""Crop NISAR GUNW layers to an area of interest over HTTP range reads (new in nasa-in-mining).

Output follows the catalog layout already used by the extracted modules:
    <data>/GUNW/<granule>/_DONE, *unwrappedPhase.tif, *coherenceMagnitude.tif, *connectedComponents.tif,
                           wrappedInterferogram_HH_coherenceMagnitude.tif (20 m), masks, radar_geometry.npz,
                           provenance.json
Values are copied without resampling: the crop window is aligned on the product grid. NISAR x/y coordinates
are pixel centres (checked: 20 m and 80 m grids share the same pixel edges), so the GeoTIFF origin is the
first centre minus half a pixel. Fill values are preserved (NaN for float layers, the declared fill otherwise).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.transform import from_origin

from .remote import RangeFile

GRID = "science/LSAR/GUNW/grids/frequencyA"
META = "science/LSAR/GUNW/metadata/processingInformation"
LAYERS = {
    # output file name: (grid, dataset path relative to GRID)
    "unwrappedInterferogram_HH_unwrappedPhase.tif": ("unwrappedInterferogram", "unwrappedInterferogram/HH/unwrappedPhase"),
    "unwrappedInterferogram_HH_coherenceMagnitude.tif": ("unwrappedInterferogram", "unwrappedInterferogram/HH/coherenceMagnitude"),
    "unwrappedInterferogram_HH_connectedComponents.tif": ("unwrappedInterferogram", "unwrappedInterferogram/HH/connectedComponents"),
    "unwrappedInterferogram_mask.tif": ("unwrappedInterferogram", "unwrappedInterferogram/mask"),
    "wrappedInterferogram_HH_coherenceMagnitude.tif": ("wrappedInterferogram", "wrappedInterferogram/HH/coherenceMagnitude"),
    "wrappedInterferogram_mask.tif": ("wrappedInterferogram", "wrappedInterferogram/mask"),
}
IDENT = ["productVersion", "productSpecificationVersion", "compositeReleaseId", "processingDateTime", "productDoi",
         "orbitPassDirection", "lookDirection", "trackNumber", "frameNumber", "referenceZeroDopplerStartTime",
         "secondaryZeroDopplerStartTime", "isFullFrame", "processingType", "granuleId"]
PARAMS = {
    "unwrapped_azimuth_looks": "parameters/unwrappedInterferogram/frequencyA/numberOfAzimuthLooks",
    "unwrapped_range_looks": "parameters/unwrappedInterferogram/frequencyA/numberOfRangeLooks",
    "wrapped_azimuth_looks": "parameters/wrappedInterferogram/frequencyA/numberOfAzimuthLooks",
    "wrapped_range_looks": "parameters/wrappedInterferogram/frequencyA/numberOfRangeLooks",
    "azimuth_iono_applied": "parameters/geocoding/azimuthIonosphericCorrectionApplied",
    "range_iono_applied": "parameters/geocoding/rangeIonosphericCorrectionApplied",
    "hydrostatic_tropo_applied": "parameters/geocoding/hydrostaticTroposphericCorrectionApplied",
    "wet_tropo_applied": "parameters/geocoding/wetTroposphericCorrectionApplied",
    "topographic_flattening_applied": "parameters/unwrappedInterferogram/frequencyA/topographicFlatteningApplied",
    "software_version": "algorithms/softwareVersion",
    "unwrapping_algorithm": "algorithms/unwrapping/unwrappingAlgorithm",
    "multilooking": "algorithms/interferogramFormation/multilooking",
    "dem_source": "inputs/demSource",
}


def _scalar(ds):
    v = ds[()]
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return [x.decode() if isinstance(x, bytes) else x.item() if isinstance(x, np.generic) else x for x in v.tolist()]
    return v


def _window(x: np.ndarray, y: np.ndarray, aoi: tuple[float, float, float, float]):
    """Index slices of the pixels whose centres fall inside aoi = (xmin, ymin, xmax, ymax) in the grid CRS."""
    xmin, ymin, xmax, ymax = aoi
    cols = np.nonzero((x >= xmin) & (x <= xmax))[0]
    rows = np.nonzero((y >= ymin) & (y <= ymax))[0]
    if cols.size == 0 or rows.size == 0:
        return None
    return slice(int(rows[0]), int(rows[-1]) + 1), slice(int(cols[0]), int(cols[-1]) + 1)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(url: str, granule_id: str, out_root: Path, aoi_utm: tuple[float, float, float, float],
            epsg_expected: int = 32629, overwrite: bool = False) -> dict:
    """Crop one GUNW granule. Returns its provenance record (also written as provenance.json)."""
    folder = Path(out_root) / "GUNW" / granule_id
    done = folder / "_DONE"
    if done.exists() and not overwrite:
        return json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    folder.mkdir(parents=True, exist_ok=True)
    rf = RangeFile(url)
    record: dict = {"granule_id": granule_id, "source_url": url, "source_size_bytes": rf.size,
                    "aoi_utm": list(aoi_utm), "epsg": None, "layers": {}, "identification": {},
                    "processing": {}, "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "method": "HTTP range read of the original HDF5; no resampling; aligned crop on product grid"}
    with h5py.File(rf, "r") as h5:
        ident = h5["science/LSAR/identification"]
        record["identification"] = {k: _scalar(ident[k]) for k in IDENT if k in ident}
        for key, path in PARAMS.items():
            full = f"{META}/{path}"
            record["processing"][key] = _scalar(h5[full]) if full in h5 else None
        freq = float(h5[f"{GRID}/centerFrequency"][()])
        record["center_frequency_hz"] = freq
        for fname, (grid, rel) in LAYERS.items():
            g = h5[f"{GRID}/{grid}"]
            epsg = int(g["projection"][()])
            if epsg != epsg_expected:
                raise ValueError(f"{granule_id}: grid EPSG {epsg} differs from the expected {epsg_expected}")
            record["epsg"] = epsg
            x, y = g["xCoordinates"][()], g["yCoordinates"][()]
            dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
            win = _window(x, y, aoi_utm)
            if win is None:
                raise ValueError(f"{granule_id}: the AOI is outside the {grid} grid")
            ds = h5[f"{GRID}/{rel}"]
            arr = ds[win]
            fill = ds.attrs.get("_FillValue")
            fill = None if fill is None else float(fill)
            transform = from_origin(float(x[win[1].start]) - dx / 2, float(y[win[0].start]) - dy / 2, abs(dx), abs(dy))
            nodata = np.nan if arr.dtype.kind == "f" else (None if fill is None or not math.isfinite(fill) else fill)
            path = folder / fname
            with rasterio.open(path, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                               dtype=arr.dtype, crs=f"EPSG:{epsg}", transform=transform, nodata=nodata,
                               compress="deflate", tiled=False) as dst:
                dst.write(arr, 1)
                units = ds.attrs.get("units")
                dst.update_tags(source_dataset=f"{GRID}/{rel}", granule=granule_id,
                                units=units.decode() if isinstance(units, bytes) else str(units))
            record["layers"][fname] = {
                "dataset": f"{GRID}/{rel}", "grid": grid, "spacing_m": [dx, dy], "shape": list(arr.shape),
                "rows": [win[0].start, win[0].stop], "cols": [win[1].start, win[1].stop],
                "units": (ds.attrs.get("units").decode() if isinstance(ds.attrs.get("units"), bytes)
                          else ds.attrs.get("units")),
                "fill_value": fill if fill is None or math.isfinite(fill) else "NaN", "sha256": _sha256(path)}
    np.savez_compressed(folder / "radar_geometry.npz", centerFrequency=freq)
    record["bytes_transferred"] = rf.bytes_read
    record["range_requests"] = rf.requests
    (folder / "provenance.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    done.write_text(json.dumps({"provenance": "provenance.json"}), encoding="utf-8")
    return record
