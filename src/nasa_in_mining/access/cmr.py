"""NASA CMR granule search (public, no credential). New in nasa-in-mining, v2 with pagination.

Catalogue presence is recorded as such: it does not prove that a product can be downloaded or used.
Pagination uses the CMR-Search-After header; the number of unique granules is checked against CMR-Hits.
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
           page_size: int = 200) -> tuple[list[Granule], dict]:
    """bbox = (west, south, east, north) in WGS84. Returns (granules, completeness record)."""
    params = {"short_name": collection, "bounding_box": ",".join(map(str, bbox)), "page_size": page_size,
              "sort_key": "start_date"}
    if temporal:
        params["temporal"] = temporal
    headers = {"User-Agent": USER_AGENT}
    found: dict[str, Granule] = {}
    hits, pages = None, 0
    while True:
        r = requests.get(CMR, params=params, headers=headers, timeout=60)
        r.raise_for_status()
        pages += 1
        hits = int(r.headers.get("CMR-Hits", hits or 0))
        entries = r.json()["feed"]["entry"]
        for e in entries:
            urls = [link["href"] for link in e.get("links", []) if link.get("href", "").startswith("https://")
                    and link["href"].endswith(".h5") and "QA_STATS" not in link["href"]
                    and "PRIVATE" not in link["href"]]
            size = e.get("granule_size")
            found.setdefault(e["id"], Granule(collection=collection, concept_id=e["id"], granule_id=e["title"],
                                              time_start=e.get("time_start"), time_end=e.get("time_end"),
                                              updated=e.get("updated"), size_mb=float(size) if size else None,
                                              data_url=urls[0] if urls else None, footprint=e.get("polygons")))
        after = r.headers.get("CMR-Search-After")
        if not entries or not after or len(found) >= hits:
            break
        headers = {**headers, "CMR-Search-After": after}
        if pages > 500:
            raise RuntimeError("CMR pagination did not terminate")
    if hits is not None and len(found) != hits:
        raise RuntimeError(f"CMR search incomplete for {collection}: {len(found)} unique granules for {hits} hits")
    record = {"pages": pages, "cmr_hits": hits, "n_unique": len(found), "complete": len(found) == hits}
    return sorted(found.values(), key=lambda g: g.granule_id), record
