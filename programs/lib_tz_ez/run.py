"""
Script to fetch and display timezone and dawn/sunrise info for airports.
Requires: astral, timezonefinder, requests
Install with: pip install astral timezonefinder requests
"""

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun, sunrise, sunset, dawn, dusk
from timezonefinder import TimezoneFinder
import pytz

try:
    # When run as a module (python -m tz_ez_lib.run)
    from .airport_data import AirportData
    from .aircraft_data import AircraftData
except ImportError:
    # When run directly (python tz_ez_lib/run.py)
    from airport_data import AirportData
    from aircraft_data import AircraftData


_DEFAULTS_FILE = os.path.join(os.path.dirname(__file__), "user_defaults.json")
# Keys that are never saved as defaults (they are one-shot actions or per-run inputs).
_NEVER_SAVE = {"save_defaults", "clear_defaults", "date", "airport"}


def load_defaults() -> dict:
    """Return saved default arg values, or an empty dict if none are saved."""
    if os.path.exists(_DEFAULTS_FILE):
        try:
            with open(_DEFAULTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_defaults(explicit: dict) -> None:
    """Persist a dict of arg values to the defaults file."""
    try:
        with open(_DEFAULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(explicit, f, indent=2)
    except Exception as e:
        print(f"⚠ Could not save defaults: {e}")


def supports_color() -> bool:
    """Return True when stdout appears to support ANSI colors."""
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    return os.getenv("TERM", "").lower() != "dumb"


USE_COLOR = supports_color()


def colorize(text: str, ansi_code: str) -> str:
    """Wrap text in ANSI color codes only when terminal color is supported."""
    if not USE_COLOR:
        return text
    return f"\033[{ansi_code}m{text}\033[0m"


def get_timezone(lat, lon):
    """Get timezone string from coordinates."""
    tf = TimezoneFinder()
    return tf.timezone_at(lat=lat, lng=lon)

def format_gmt_time(local_time):
    """Format GMT time with day indicator if different day."""
    gmt_time = local_time.astimezone(pytz.UTC)
    gmt_str = gmt_time.strftime('%H:%M GMT')
    if local_time.date() != gmt_time.date():
        gmt_str += " *"
    return colorize(gmt_str, "92")

def calculate_sun_times(lat, lon, tz_str, date=None, search_window_days: int = 1):
    """Calculate sunrise, sunset, and twilight times.

    Astral may raise a ValueError when dawn/dusk do not exist (e.g. polar day/night).
    This function is resilient: it will try nearby dates for sunrise/sunset within
    the configured search window and will return None for civil twilight if it
    cannot be computed.
    """
    if date is None:
        date = datetime.now().date()
    if search_window_days < 0:
        raise ValueError("Sun search window must be 0 or greater.")

    # Create location info
    location = LocationInfo("Airport", "Region", timezone=tz_str, latitude=lat, longitude=lon)

    def _try_adjacent_dates(fn):
        """Try to compute a sun time for nearby dates within the configured search window."""
        candidate_dates = [date]
        for offset in range(1, search_window_days + 1):
            candidate_dates.append(date - timedelta(days=offset))
            candidate_dates.append(date + timedelta(days=offset))

        last_error = None
        for d in candidate_dates:
            try:
                return fn(location.observer, date=d, tzinfo=tz_str)
            except ValueError as exc:
                last_error = exc
                continue
        # If we fall through, there was no valid time on any of the checked dates.
        raise ValueError(
            f"No {fn.__name__} found within ±{search_window_days} day(s) of {date} "
            f"for coordinates {lat}, {lon}."
        ) from last_error

    # Compute sunrise/sunset (required). If it fails, let the caller handle it.
    sunrise_time = _try_adjacent_dates(sunrise)
    sunset_time = _try_adjacent_dates(sunset)

    # Civil twilight (dawn/dusk) is optional; it may not exist at high latitudes.
    civil_dawn = None
    civil_dusk = None
    try:
        civil_dawn = dawn(location.observer, date=date, tzinfo=tz_str)
        civil_dusk = dusk(location.observer, date=date, tzinfo=tz_str)
    except ValueError:
        # No civil twilight on this date (e.g. polar day/night). That's okay.
        pass

    return {
        "civil_twilight_begin": civil_dawn,
        "civil_twilight_end": civil_dusk,
        "sunrise": sunrise_time,
        "sunset": sunset_time,
    }


def parse_date(date_input: str):
    """Parse a date string (MM-DD-YYYY or MM-DD) and return a date object."""
    date_input = date_input.strip()
    if not date_input:
        return datetime.now().date()

    if "-" in date_input:
        parts = date_input.split("-")
    elif "/" in date_input:
        parts = date_input.split("/")
    else:
        raise ValueError("Invalid date format. Use MM-DD-YYYY or MM-DD.")

    if len(parts) == 2:
        month, day = map(int, parts)
        year = datetime.now().year
    elif len(parts) == 3:
        month, day, year = map(int, parts)
    else:
        raise ValueError("Unexpected number of date parts.")

    return datetime(year, month, day).date()


def parse_retry_input(retry_input: str):
    """Interpret retry prompt input as quit or a date (blank means today)."""
    retry_input = retry_input.strip()
    if not retry_input:
        return ("date", datetime.now().date())

    if retry_input.lower() in ("q", "quit", "exit"):
        return ("quit", None)

    return ("date", parse_date(retry_input))


def build_logging_night_url(airport: str, date: datetime):
    """Build a URL for logging night data to a Google Form."""
    url = f"https://loggingnight.org/?airport={airport}&date={date.year}-{date.month:02d}-{date.day:02d}"
    return url


def build_adsb_url(icao_hex: str, lat: float, lon: float, date: datetime) -> str:
    """Build an ADS-B Exchange globe URL for a given aircraft, location, and date."""
    date_str = f"{date.year}-{date.month:02d}-{date.day:02d}"
    return f"https://globe.adsbexchange.com/?icao={icao_hex}&lat={lat:.3f}&lon={lon:.3f}&zoom=9.0&showTrace={date_str}"


def display_airport_info(
    airport_data: AirportData,
    iata_code: str,
    date=None,
    show_twilight: bool = True,
    sun_search_window_days: int = 1,
    aircraft: str | None = None,
    aircraft_data: AircraftData | None = None,
    open_adsb: bool = False,
):
    """Fetch and display info for an airport on a given date."""
    airport_info = airport_data.get_airport_info(iata_code)
    iata_code = iata_code.upper()

    # If not found in OpenFlights, allow manual entry and retry.
    if not airport_info:
        if airport_data.prompt_add_airport(iata_code):
            airport_info = airport_data.get_airport_info(iata_code)
        else:
            print(f"✗ Airport {iata_code} not found in database")
            return False

    if not airport_info:
        print(f"✗ Airport {iata_code} not found in database")
        return False

    lat, lon, name = airport_info

    try:
        # Get timezone
        tz_str = get_timezone(lat, lon)
        if not tz_str:
            print(f"✗ Could not determine timezone for {iata_code}")
            return False

        # Get sun times for requested date (None means today)
        sun_times = calculate_sun_times(
            lat,
            lon,
            tz_str,
            date,
            search_window_days=sun_search_window_days,
        )

        # Create timezone-aware datetimes
        tz = pytz.timezone(tz_str)

        # Determine a sample datetime for determining tz abbreviation / offset
        date_note = date if date is not None else datetime.now().date()
        try:
            sample_dt = tz.localize(datetime(date_note.year, date_note.month, date_note.day, 12, 0))
        except Exception:
            # In rare cases (ambiguous/non-existent times), fall back to now
            sample_dt = datetime.now(tz)

        tz_abbrev = sample_dt.tzname() or ""
        offset = sample_dt.utcoffset() or timedelta(0)
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        abs_minutes = abs(total_minutes)
        offset_hours = abs_minutes // 60
        offset_minutes = abs_minutes % 60
        gmt_offset = f"GMT{sign}{offset_hours}"
        if offset_minutes:
            gmt_offset += f":{offset_minutes:02d}"

        # Convert times to local timezone (only convert civil twilight if present)
        civil_dawn = None
        civil_dusk = None
        if sun_times.get("civil_twilight_begin"):
            civil_dawn = sun_times["civil_twilight_begin"].astimezone(tz)
        if sun_times.get("civil_twilight_end"):
            civil_dusk = sun_times["civil_twilight_end"].astimezone(tz)

        sunrise = sun_times.get("sunrise").astimezone(tz) #type: ignore
        sunset = sun_times.get("sunset").astimezone(tz) #type: ignore

        # Calculate 1 hour before/after sunrise
        one_hr_before_sunrise = sunrise - timedelta(hours=1)
        one_hr_after_sunset = sunset + timedelta(hours=1)

        # Add a note if sunrise/sunset come from a different date (e.g. polar day/night fallbacks)
        date_note = date if date is not None else datetime.now().date()
        sunrise_note = "" if sunrise.date() == date_note else f" (using {sunrise.date()})"
        sunset_note = "" if sunset.date() == date_note else f" (using {sunset.date()})"

        # Display info
        print(f"\n{'='*60}")
        print(f"Airport: {colorize(f'{iata_code} - {name}', '96')}")
        print(f"Timezone: {tz_str} -> {tz_abbrev} ({gmt_offset}) for {date_note}")
        print(f"Logging Night URL: {build_logging_night_url(iata_code, datetime(date_note.year, date_note.month, date_note.day))}")
        if aircraft and aircraft_data:
            icao_hex = aircraft_data.get_icao(aircraft)
            if icao_hex:
                adsb_url = build_adsb_url(icao_hex, lat, lon, datetime(date_note.year, date_note.month, date_note.day))
                if open_adsb:
                    webbrowser.open(adsb_url)
                    print(f"ADS-B Exchange: opened in browser ({adsb_url})")
                else:
                    print(f"ADS-B Exchange URL: {adsb_url}")
            else:
                print(f"✗ ADS-B URL: '{aircraft}' not found in FAA registry")
        print()
        # Only show civil twilight if requested and both dawn and dusk are available
        if show_twilight and civil_dawn and civil_dusk:
            print(f" Civil Twilight Begin:   {civil_dawn.strftime('%H:%M %Z')} ({format_gmt_time(civil_dawn)})    ->    ({format_gmt_time(civil_dusk)}) {civil_dusk.strftime('%H:%M %Z')}    :Civil Twilight End")
        # print(f"Sunrise:               {sunrise.strftime('%H:%M:%S %Z')} ({sunrise.astimezone(pytz.UTC).strftime('%H:%M:%S GMT')})")
        print(f"1 Hour Before Sunrise:   {one_hr_before_sunrise.strftime('%H:%M %Z')} ({format_gmt_time(one_hr_before_sunrise)}){sunrise_note}    ->    ({format_gmt_time(one_hr_after_sunset)}){sunset_note} {one_hr_after_sunset.strftime('%H:%M %Z')}    :1 Hour After Sunset")
        # print(f"{'='*60}")
        # print("* GMT time is on a different day than the local time")

        return True

    except Exception as e:
        print(f"✗ Error processing {iata_code}: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Airport Timezone and Dawn/Sunrise Information (uses OpenFlights airport database)"
    )
    parser.add_argument(
        "-a",
        "--airport",
        "--airports",
        nargs="+",
        help="Airport codes (IATA 3-letter or ICAO 4-letter) to display info for.",
    )
    parser.add_argument(
        "-d",
        "--date",
        help="Date to use (MM-DD-YYYY or MM-DD, current year assumed if omitted).",
    )
    parser.add_argument(
        "-nt",
        "--No-Twilight",
        dest="no_twilight",
        action="store_true",
        help="Do not display civil twilight (dawn/dusk) times.",
    )
    parser.add_argument(
        "-c",
        "--aircraft",
        default=None,
        help="Aircraft N-number (e.g. N971MC) to generate an ADS-B Exchange URL (optional).",
    )
    parser.add_argument(
        "-o",
        "--open-adsb",
        dest="open_adsb",
        action="store_true",
        help="Open ADS-B Exchange links in the browser instead of printing them.",
    )
    parser.add_argument(
        "--sun-search-window-days",
        type=int,
        default=1,
        help=(
            "Number of days before/after the requested date to search for sunrise/sunset "
            "when the requested date has no result. Default: 1."
        ),
    )
    parser.add_argument(
        "--save-defaults",
        dest="save_defaults",
        action="store_true",
        help="Save the current arguments as defaults for future runs.",
    )
    parser.add_argument(
        "--clear-defaults",
        dest="clear_defaults",
        action="store_true",
        help="Clear all saved default arguments.",
    )

    # Apply any previously saved defaults before parsing.
    saved = load_defaults()
    if saved:
        parser.set_defaults(**saved)

    # Parse with a clean copy of defaults so we can detect what was explicitly
    # passed on this invocation (for --save-defaults).
    bare_defaults = vars(parser.parse_args([]))
    args = parser.parse_args()

    # --clear-defaults: wipe the file and exit.
    if args.clear_defaults:
        if os.path.exists(_DEFAULTS_FILE):
            os.remove(_DEFAULTS_FILE)
            print("Defaults cleared.")
        else:
            print("No saved defaults to clear.")
        return

    # --save-defaults: persist args that differ from argparse's bare defaults.
    if args.save_defaults:
        current = vars(args)
        to_save = {
            k: v for k, v in current.items()
            if k not in _NEVER_SAVE and v != bare_defaults.get(k)
        }
        save_defaults(to_save)
        if to_save:
            print(f"Defaults saved: {to_save}")
        else:
            print("No non-default arguments to save.")

    show_twilight = not args.no_twilight
    if args.sun_search_window_days < 0:
        print("✗ Invalid sun search window: value must be 0 or greater.")
        return

    print("Airport Timezone and Dawn/Sunrise Information")
    print("-" * 60)

    airport_data = AirportData()
    if not airport_data.fetch_airport_data():
        return

    aircraft_data = AircraftData()

    date_obj = None
    if args.date:
        try:
            date_obj = parse_date(args.date)
        except ValueError as e:
            print(f"✗ Invalid date: {e}")
            return

    if args.airport:
        airports = [a.strip() for a in args.airport if a.strip()]
        if not airports:
            print("✗ No airport codes provided.")
            return

        successful = 0
        for airport in airports:
            if display_airport_info(
                airport_data,
                airport,
                date_obj,
                show_twilight=show_twilight,
                sun_search_window_days=args.sun_search_window_days,
                aircraft=args.aircraft,
                aircraft_data=aircraft_data,
                open_adsb=args.open_adsb,
            ):
                successful += 1

        print()
        print(f"Processed {successful}/{len(airports)} airports successfully")
        return

    while True:
        # Get user input
        # Ask for date first (unless given on command line)
        if date_obj is None:
            date_input = input(
                "\nEnter a date (MM-DD-YYYY or MM-DD) or leave blank for today (or type 'q' to quit): "
            ).strip()
            if date_input.lower() in ("q", "quit", "exit"):
                break

            if date_input:
                try:
                    date_obj = parse_date(date_input)
                except ValueError:
                    print("Invalid date format. Please use MM-DD-YYYY or MM-DD.")
                    continue
            else:
                date_obj = datetime.now().date()
        else:
            # Use date provided via args for all iterations
            # print(f"Using date: {date_obj}")
            pass

        aircraft_input = input(
            "Enter aircraft N-number (optional, e.g. N971MC, or leave blank to skip): "
        ).strip()
        aircraft = aircraft_input if aircraft_input else None

        airports = airport_data.prompt_airports_from_user()
        if not airports:
            # If the user didn't enter any airports, offer to quit or retry.
            cont = input("No airports entered. Press Enter to try again or type 'q' to quit: ").strip().lower()
            if cont in ("q", "quit", "exit"):
                break
            continue

        # Process each airport
        successful = 0
        for airport in airports:
            if display_airport_info(
                airport_data,
                airport.strip(),
                date_obj,
                show_twilight=show_twilight,
                sun_search_window_days=args.sun_search_window_days,
                aircraft=aircraft,
                aircraft_data=aircraft_data,
                open_adsb=args.open_adsb,
            ):
                successful += 1

        print()
        print(f"Processed {successful}/{len(airports)} airports successfully")

        again = input(
            "\nEnter a date (MM-DD-YYYY or MM-DD) or leave blank for today (or type 'q' to quit): "
        )
        try:
            action, next_date = parse_retry_input(again)
        except ValueError:
            print("Invalid date format. Please use MM-DD-YYYY or MM-DD.")
            continue

        if action == "quit":
            break

        if args.date is None:
            # A date entered at the retry prompt should carry into the next airport prompt.
            date_obj = next_date if action == "date" else None

if __name__ == "__main__":
    main()
