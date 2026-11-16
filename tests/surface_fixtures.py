"""SYNTHETIC GCOV crops (test data only, never presented as observations).

6 x 6 km window, 10 m native samples (600 x 600), 20 m analysis cells (300 x 300), same zones as mining_fixtures
(study = 2 x 2 km square, control = ring). gamma-0 HH = 0.05 with a small seeded log-normal noise per date, so the
robust spread of the control is non-zero and every expected count is known: a permanent darkening of the 25 x 25
cell block (0.25 km2) from the fifth acquisition on changes only the pair (d3, d4) (-4 dB).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from rasterio.transform import from_origin

from tests import mining_fixtures as fx
from tests import support as s

N10 = 600
BLOCK = (slice(240, 290), slice(240, 290))      # 50 x 50 native samples = 25 x 25 cells = 0.25 km2, inside the study square
COLLECTION = "NISAR_L2_GCOV_PROVISIONAL_V1"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def crop(data: Path, date: str, track: int, frame: int, direction: str, power_hh: np.ndarray, power_hv: np.ndarray,
         mask: np.ndarray | None = None, exception: np.ndarray | None = None, crid: str = "P05023",
         grid_shift: float = 0.0) -> Path:
    stamp = date.replace("-", "")
    name = f"NISAR_L2_PR_GCOV_{track:03d}_{track:03d}_{direction[0].upper()}_{frame:03d}_4005_DHDH_A_{stamp}T054640_X_{crid}_N_F_J_001"
    folder = data / "GCOV" / name
    folder.mkdir(parents=True)
    tr = from_origin(fx.X0 + grid_shift, fx.Y0, 10, 10)
    mask = np.ones((N10, N10), "uint8") if mask is None else mask
    exception = np.zeros((N10, N10), "uint8") if exception is None else exception
    arrays = {"HHHH.tif": power_hh.astype("float32"), "HVHV.tif": power_hv.astype("float32"), "mask.tif": mask,
              "inputDataExceptionMask.tif": exception, "numberOfLooks.tif": np.full((N10, N10), 5.0, "float32")}
    files = {}
    for fn, arr in arrays.items():
        s.write_tif(folder / fn, arr, tr, f"EPSG:{fx.EPSG}")
        files[fn] = _sha(folder / fn)
    coarse = from_origin(fx.X0 - 1000, fx.Y0 + 1000, 1000, 1000)
    for fn, val in (("noiseEquivalentBackscatter_HH.tif", 1e-4), ("noiseEquivalentBackscatter_HV.tif", 1e-4), ("incidenceAngle.tif", 41.0)):
        s.write_tif(folder / fn, np.full((8, 8), val, "float32"), coarse, f"EPSG:{fx.EPSG}")
        files[fn] = _sha(folder / fn)
    prov = {"granule_id": name, "source_url": f"https://example.invalid/NISAR/{COLLECTION}/{name}/{name}.h5",
            "polarizations": ["HH", "HV"], "native_spacing_m": [10.0, 10.0], "bytes_transferred": 0, "files": files,
            "identification": {"trackNumber": track, "frameNumber": frame, "orbitPassDirection": direction.capitalize(),
                               "zeroDopplerStartTime": f"{date}T05:46:40.000000000", "compositeReleaseId": crid,
                               "productVersion": "synthetic", "listOfObservationModes": ["(NOT SPECIFIED)"], "hasInputDataException": 0},
            "processing": {"noise_correction_applied": "False", "rtc_applied": "True", "normalization": "gamma0", "software_version": "synthetic"}}
    (folder / "provenance.json").write_text(json.dumps(prov), encoding="utf-8")
    (folder / "_DONE").write_text("{}", encoding="utf-8")
    return folder


def series(data: Path, dates: list[str], track: int, frame: int, direction: str, change_from: int | None = None,
           bad_date: int | None = None, shift_date: int | None = None, crid: str = "P05023") -> None:
    for i, d in enumerate(dates):
        rng = np.random.default_rng(1000 * track + i)
        noise = lambda: np.exp(rng.normal(0, 0.1, (N10, N10)))   # noqa: E731
        hh = 0.05 * noise()
        hv = 0.01 * noise()
        if change_from is not None and i >= change_from:
            hh[BLOCK] *= 0.4                                     # -3.98 dB
        mask = None
        if bad_date == i:
            mask = np.zeros((N10, N10), "uint8")                  # not fully focused everywhere
        crop(data, d, track, frame, direction, hh, hv, mask=mask, crid=crid, grid_shift=10.0 if shift_date == i else 0.0)


def write_case(case_dir: Path, batches: list[dict]) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1] / "cases" / "benguerir-surface-study"
    cfg = json.loads((root / "study_config.json").read_text(encoding="utf-8"))
    cfg.update(study_id="synthetic-surface-test", data_nature="synthetic", batches=batches, development_windows=[],
               site={**cfg["site"], "id": "synthetic", "name": "SYNTHETIC test site"}, v2_case="none.json", v2_verification_zones="none.geojson")
    (case_dir / "study_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copy(root / "protocol.json", case_dir / "protocol.json")
    (case_dir / "zones.geojson").write_text(json.dumps(fx._zones()), encoding="utf-8")
    return case_dir


DATES_8 = [f"2026-{m:02d}-{d:02d}" for m, d in ((1, 1), (1, 13), (1, 25), (2, 6), (2, 18), (3, 2), (3, 14), (3, 26), (4, 7))]
BATCH_ASC = {"id": "asc", "role": "main", "collection": COLLECTION, "crid": "P05023", "track": 44, "frame": 18, "direction": "ascending"}
BATCH_DESC = {"id": "desc", "role": "main", "collection": COLLECTION, "crid": "P05023", "track": 23, "frame": 72, "direction": "descending"}
