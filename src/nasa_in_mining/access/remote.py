"""Authenticated, read-only HTTP range access to cloud-hosted HDF5 products (new module).

Earthdata credentials are read from, in order: the EARTHDATA_TOKEN environment variable, the git-ignored
file `.earthdata_token` in the working directory (or MINING_TOKEN_FILE), or the user's netrc. The token is
never logged, printed or written into outputs. Only the requested byte ranges are transferred.
"""
from __future__ import annotations

from collections import OrderedDict
import io
import os
from pathlib import Path
import time

import requests

USER_AGENT = "nasa-in-mining/0.2 (research; read-only range access)"
BLOCK = 1 << 20          # 1 MiB cache blocks
MAX_BLOCKS = 256         # 256 MiB cache ceiling per open file


class CredentialsMissing(RuntimeError):
    """No Earthdata credential is configured locally."""


def earthdata_token() -> str | None:
    tok = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if tok:
        return tok
    path = Path(os.environ.get("MINING_TOKEN_FILE", Path.cwd() / ".earthdata_token"))
    if path.is_file():
        tok = path.read_text(encoding="utf-8").strip()
        return tok or None
    return None


def session(auth: bool = True) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    if auth:
        tok = earthdata_token()
        if tok:
            s.headers["Authorization"] = f"Bearer {tok}"
        # without a token, requests falls back to the user's netrc for urs.earthdata.nasa.gov
    return s


def _get(s: requests.Session, url: str, headers: dict, tries: int = 5, **kw) -> requests.Response:
    for attempt in range(tries):
        try:
            r = s.get(url, headers=headers, timeout=120, **kw)
            if r.status_code in (500, 502, 503, 504):
                raise requests.HTTPError(f"server error {r.status_code}")
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


class RangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP Range requests, with an LRU block cache.

    The protected URL is resolved once (Earthdata login + redirect to a signed URL); the signed URL is then
    read without sending the credential. It is re-resolved if it expires.
    """

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._auth = session(auth=True)
        self._plain = session(auth=False)
        self._cache: OrderedDict[int, bytes] = OrderedDict()
        self.bytes_read = 0
        self.requests = 0
        self._pos = 0
        self._resolve()

    def _resolve(self) -> None:
        r = _get(self._auth, self.url, {"Range": "bytes=0-0"}, allow_redirects=True)
        if r.status_code == 401 or "urs.earthdata.nasa.gov" in r.url:
            if not earthdata_token():
                raise CredentialsMissing("Earthdata credentials are required: set EARTHDATA_TOKEN, "
                                         "a .earthdata_token file or a netrc entry for urs.earthdata.nasa.gov")
            raise PermissionError("Earthdata refused the configured credential (expired or not authorised)")
        if r.status_code != 206:
            raise OSError(f"range request not honoured (HTTP {r.status_code})")
        self._signed = r.url
        self.size = int(r.headers["Content-Range"].split("/")[-1])

    def _block(self, i: int) -> bytes:
        if i in self._cache:
            self._cache.move_to_end(i)
            return self._cache[i]
        start, end = i * BLOCK, min((i + 1) * BLOCK, self.size) - 1
        for retry in range(2):
            r = _get(self._plain, self._signed, {"Range": f"bytes={start}-{end}"})
            if r.status_code == 206:
                break
            if r.status_code in (401, 403) and retry == 0:
                self._resolve()           # the signed URL expired
                continue
            raise OSError(f"range read failed (HTTP {r.status_code})")
        data = r.content
        self.bytes_read += len(data)
        self.requests += 1
        self._cache[i] = data
        if len(self._cache) > MAX_BLOCKS:
            self._cache.popitem(last=False)
        return data

    # io.RawIOBase interface
    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        base = {0: 0, 1: self._pos, 2: self.size}[whence]
        self._pos = max(0, base + offset)
        return self._pos

    def readinto(self, b) -> int:
        n = min(len(b), max(0, self.size - self._pos))
        if n == 0:
            return 0
        out, pos, end = memoryview(b), self._pos, self._pos + n
        while pos < end:
            i = pos // BLOCK
            blk = self._block(i)
            off = pos - i * BLOCK
            take = min(len(blk) - off, end - pos)
            out[pos - self._pos: pos - self._pos + take] = blk[off:off + take]
            pos += take
        self._pos = end
        return n
