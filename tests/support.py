from __future__ import annotations

import os
from pathlib import Path
import tempfile

# Set configuration before any processing import. No upstream directories are used.
SESSION = tempfile.TemporaryDirectory(prefix="mining_check_")
ROOT = Path(SESSION.name)
os.environ.update(MINING_DATA=str(ROOT / "data"), MINING_CACHE=str(ROOT / "cache"),
                  MINING_AUX=str(ROOT / "auxiliary"), MINING_OFFLINE="1", NISAR_DEM="none",
                  MPLCONFIGDIR=str(ROOT / "matplotlib"), PYTHONDONTWRITEBYTECODE="1")

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin
import rasterio

LAT, LON = 32.25825, -7.82355
N, PX, FREQ = 80, 1000.0, 1_239_000_000.0
X, Y = Transformer.from_crs(4326, 32629, always_xy=True).transform(LON, LAT)
TRANSFORM = from_origin(X - N / 2 * PX, Y + N / 2 * PX, PX, PX)
yy, xx = np.mgrid[:N, :N]
BUMP = np.exp(-((xx - N / 2) ** 2 + (yy - N / 2) ** 2) / 12)


def write_tif(path, arr, transform=TRANSFORM, crs="EPSG:32629"):
    with rasterio.open(path, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                       dtype=arr.dtype, crs=crs, transform=transform, nodata=np.nan if arr.dtype.kind == "f" else None) as ds:
        ds.write(arr, 1)


def product_dir(data, level, ref, sec, crid="P05023"):
    name = (f"NISAR_L2_PR_{level}_030_044_A_017_031_4000_SH_{ref}T053852_{ref}T053900_"
            f"{sec}T053852_{sec}T053900_{crid}_N_F_J_001")
    folder = data / level / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def make_products(data):
    rng = np.random.default_rng(123)
    for i, (a, b) in enumerate((("20260101", "20260113"), ("20260113", "20260125"), ("20260125", "20260206"))):
        folder = product_dir(data, "GUNW", a, b)
        los_cm = 2 * BUMP + rng.normal(0, 0.03, BUMP.shape)
        phase = (-los_cm / 100 * 4 * np.pi / (299_792_458 / FREQ)).astype("float32")
        coh = (np.full(BUMP.shape, 0.85) - (0.55 * BUMP if i == 2 else 0)).astype("float32")
        write_tif(folder / "unwrappedInterferogram_HH_unwrappedPhase.tif", phase)
        write_tif(folder / "unwrappedInterferogram_HH_coherenceMagnitude.tif", coh)
        write_tif(folder / "unwrappedInterferogram_HH_connectedComponents.tif", np.ones(BUMP.shape, "uint16"))
        np.savez_compressed(folder / "radar_geometry.npz", centerFrequency=FREQ)
        (folder / "_DONE").write_text("{}", encoding="utf-8")
    return data
