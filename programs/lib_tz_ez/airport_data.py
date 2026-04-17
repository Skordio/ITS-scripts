"""Airport data fetching and lookup utilities.

This module provides a reusable class for fetching airport data (from OpenFlights and
user overrides), looking up airport coordinates by IATA/ICAO code, and optionally
prompting the user to add missing airports.

The class is designed to be used by scripts (such as tz_ez/run.py) or other modules
that need to work with airport codes and coordinates.
"""

import os
import csv
import io
import re
import requests


class AirportData:
    """Manage airport data and lookups."""

    OPENFLIGHTS_URL = (
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
    )

    def __init__(self, user_airports_file: str | None = None, openflights_url: str | None = None):
        self._airport_cache: dict[str, tuple[float, float, str]] = {}
        self.user_airports_file = (
            user_airports_file
            if user_airports_file is not None
            else os.path.join(os.path.dirname(__file__), "user_airports.csv")
        )
        self.openflights_url = openflights_url or self.OPENFLIGHTS_URL

    def fetch_airport_data(self) -> dict[str, tuple[float, float, str]] | None:
        """Fetch airport data from OpenFlights and load any user-defined airports."""
        if self._airport_cache:
            return self._airport_cache

        print("Fetching airport data from OpenFlights database...")

        try:
            response = requests.get(self.openflights_url, timeout=10)
            response.raise_for_status()

            self._parse_openflights_data(response.text)

            # Load user-defined airports (overrides duplicates)
            self.load_user_airports()

            print(f"Successfully loaded {len(self._airport_cache)} airports from OpenFlights database.\n")
            return self._airport_cache

        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching airport data: {e}")
            print("✗ Could not fetch airport data. Loading locally stored airports (if any)...")
            self.load_user_airports()
            if self._airport_cache:
                print(f"Loaded {len(self._airport_cache)} locally stored airports.\n")
                return self._airport_cache
            print("✗ No local airport data available. Cannot proceed.")
            return None

    def _parse_openflights_data(self, data: str) -> None:
        """Parse OpenFlights airports.dat CSV text into the cache."""
        csv_reader = csv.reader(io.StringIO(data))
        for row in csv_reader:
            if len(row) >= 8:
                try:
                    iata = row[4].strip()
                    icao = row[5].strip()
                    name = row[1].strip()
                    lat = float(row[6])
                    lon = float(row[7])

                    if iata and len(iata) == 3 and iata != "\\N":
                        self._airport_cache[iata.upper()] = (lat, lon, name)
                    if icao and len(icao) == 4 and icao != "\\N":
                        self._airport_cache[icao.upper()] = (lat, lon, name)
                except (ValueError, IndexError):
                    continue

    def load_user_airports(self) -> None:
        """Load manually added airport entries from the local CSV file."""
        if not os.path.isfile(self.user_airports_file):
            return

        try:
            with open(self.user_airports_file, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 4:
                        continue
                    code, lat_str, lon_str, name = row[:4]
                    code = code.strip().upper()
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                    except ValueError:
                        continue
                    if code:
                        self._airport_cache[code] = (lat, lon, name)
        except Exception:
            # Ignore malformed user file; we don't want to crash the script.
            pass

    def save_user_airport(self, code: str, lat: float, lon: float, name: str | None = None) -> None:
        """Append a manually added airport entry to the local CSV file."""
        try:
            header = False
            if not os.path.isfile(self.user_airports_file):
                header = True
            with open(self.user_airports_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if header:
                    writer.writerow(["code", "lat", "lon", "name"])
                writer.writerow([code.upper(), lat, lon, name or ""])
        except Exception:
            # If we can't write, just keep it in memory.
            pass

    def get_airport_info(self, iata_code: str) -> tuple[float, float, str] | None:
        """Get latitude/longitude and name for an airport code."""
        if not iata_code:
            return None
        iata_upper = iata_code.upper()

        if len(iata_upper) == 3:
            icao_attempt = "K" + iata_upper
            if icao_attempt in self._airport_cache:
                return self._airport_cache[icao_attempt]

        return self._airport_cache.get(iata_upper)  # falls back to direct IATA lookup for international airports

    def prompt_add_airport(
        self,
        iata_code: str,
        input_func=input,
        print_func=print,
    ) -> bool:
        """Prompt the user to manually add an airport when not found."""
        iata_code = iata_code.strip().upper()
        print_func(f"\nAirport '{iata_code}' not found in database.")
        resp = input_func("Would you like to add it manually? (y/N): ").strip().lower()
        if resp not in ("y", "yes"):
            return False

        while True:
            coords = input_func(
                "Enter latitude and longitude separated by a comma (e.g. 40.6413,-73.7781), or leave blank to cancel: "
            ).strip()
            if not coords:
                return False
            parts = [p.strip() for p in coords.split(",") if p.strip()]
            if len(parts) != 2:
                print_func("Please enter two values separated by a comma.")
                continue
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                break
            except ValueError:
                print_func("Invalid coordinates. Please enter numeric latitude and longitude.")

        name = input_func("Optional airport name (press Enter to skip): ").strip()
        name = name or iata_code
        self._airport_cache[iata_code] = (lat, lon, name)
        self.save_user_airport(iata_code, lat, lon, name)
        print_func(f"Added {iata_code} -> {lat},{lon} to local airport list.\n")
        return True

    def prompt_airports_from_user(self, input_func=input, print_func=print) -> list[str] | None:
        """Ask the user for a list of airport codes and return a cleaned list."""
        airport_list = input_func(
            "Enter airport codes separated by spaces (IATA 3-letter or ICAO 4-letter codes, e.g., JFK KJFK LAX KLAX): "
        ).strip()
        airport_list = re.sub(r"[^a-zA-Z0-9\s]", " ", airport_list)
        if not airport_list:
            print_func("No airports entered. Exiting.")
            return None
        return [code for code in airport_list.split() if code.strip()]
