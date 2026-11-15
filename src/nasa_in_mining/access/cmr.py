"""NASA CMR granule search (public, no credential). New in nasa-in-mining.

Catalogue presence is recorded as such: it does not prove that a product can be downloaded or used.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import requests

from .remote import USER_AGENT

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"


@dataclass
class Granule:
    collection: str
    concept_id: str
    granule_id: str
    time_start: str
    time_end: str
    updated: str
    size_mb: float | None
    data_url: str | None
    footprint: list | None

    def to_dict(self) -> dict:
        return asdict(self)


def search(collection: str, bbox: tuple[float, float, float, float], temporal: str | None = None,
           page_size: int = 2000) -> list[Granule]:
    """bbox = (west, south, east, north) in WGS84."""
    params = {"short_name": collection, "bounding_box": ",".join(map(str, bbox)), "page_size": page_size}
    if temporal:
        params["temporal"] = temporal
    r = requests.get(CMR, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    out = []
    for e in r.json()["feed"]["entry"]:
        urls = [link["href"] for link in e.get("links", []) if link.get("href", "").startswith("https://")
                and link["href"].endswith(".h5") and "QA_STATS" not in link["href"]
                and "PRIVATE" not in link["href"]]
        size = e.get("granule_size")
        out.append(Granule(collection=collection, concept_id=e["id"], granule_id=e["title"],
                           time_start=e.get("time_start"), time_end=e.get("time_end"), updated=e.get("updated"),
                           size_mb=float(size) if size else None, data_url=urls[0] if urls else None,
                           footprint=e.get("polygons")))
    return sorted(out, key=lambda g: g.granule_id)
