"""FAA aircraft registry lookup for exact N-number to ICAO Mode S hex address.

Downloads the FAA releasable aircraft database and caches a slim N-number →
ICAO hex index locally.  The full ZIP is ~20 MB; only the two relevant columns
are kept in the cache file, which is typically a few MB.

Cache location: same directory as this file (faa_registry_icao.csv).
Cache validity: 30 days (the FAA publishes weekly updates; daily accuracy is
not required here).
"""

import csv
import io
import os
import zipfile
from datetime import datetime, timedelta

import requests

FAA_REGISTRY_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"
CACHE_FILE_NAME = "faa_registry_icao.csv"
CACHE_MAX_AGE_DAYS = 30


class AircraftData:
    """Look up exact ICAO 24-bit Mode S hex addresses from the FAA aircraft registry."""

    def __init__(self, cache_file: str | None = None):
        self.cache_file = cache_file or os.path.join(
            os.path.dirname(__file__), CACHE_FILE_NAME
        )
        self._icao_map: dict[str, str] = {}  # bare N-number (no prefix) → icao hex

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_icao(self, n_number: str) -> str | None:
        """Return the ICAO hex address for an N-number, or None if not found.

        Loads the cache on first call, downloading from the FAA if needed.
        """
        if not self._icao_map:
            self._ensure_loaded()
        key = self._normalize(n_number)
        return self._icao_map.get(key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(n_number: str) -> str:
        """Strip the N prefix and uppercase, matching the FAA registry format."""
        n = n_number.upper().strip()
        if n.startswith("N"):
            n = n[1:]
        return n

    def _cache_is_fresh(self) -> bool:
        if not os.path.exists(self.cache_file):
            return False
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.cache_file))
        return age < timedelta(days=CACHE_MAX_AGE_DAYS)

    def _load_cache(self) -> None:
        self._icao_map = {}
        with open(self.cache_file, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    self._icao_map[row[0]] = row[1]

    def _download_and_cache(self) -> None:
        print("Downloading FAA aircraft registry (this may take a moment)...")
        try:
            resp = requests.get(FAA_REGISTRY_URL, timeout=120)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Could not download FAA registry: {e}") from e

        icao_map: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            master_name = next(
                (name for name in zf.namelist() if name.upper() == "MASTER.TXT"),
                None,
            )
            if master_name is None:
                raise RuntimeError("MASTER.TXT not found in FAA registry ZIP")
            with zf.open(master_name) as raw:
                reader = csv.DictReader(
                    io.TextIOWrapper(raw, encoding="latin-1")
                )
                for row in reader:
                    n_num = (row.get("N-NUMBER") or "").strip().upper()
                    icao_hex = (row.get("MODE S CODE HEX") or "").strip().lower()
                    if n_num and icao_hex:
                        icao_map[n_num] = icao_hex

        # Write slim cache (N-NUMBER,ICAO_HEX only)
        with open(self.cache_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for n, icao in icao_map.items():
                writer.writerow([n, icao])

        self._icao_map = icao_map
        print(f"FAA registry cached ({len(icao_map):,} aircraft) at {self.cache_file}")

    def _ensure_loaded(self) -> None:
        if self._cache_is_fresh():
            self._load_cache()
            return

        stale_exists = os.path.exists(self.cache_file)
        try:
            self._download_and_cache()
        except RuntimeError as e:
            if stale_exists:
                print(f"⚠ {e}. Using stale cache.")
                self._load_cache()
            else:
                print(f"⚠ {e}. No cached registry available; ADS-B URLs will be skipped.")
