"""
Script to fetch and display timezone and dawn/sunrise info for airports.
Requires: astral, timezonefinder, requests
Install with: pip install astral timezonefinder requests
"""

import argparse
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun, sunrise, sunset, dawn, dusk
from timezonefinder import TimezoneFinder
import pytz

try:
    # When run as a module (python -m tz_ez_lib.run)
    from .airport_data import AirportData
except ImportError:
    # When run directly (python tz_ez_lib/run.py)
    from airport_data import AirportData


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
    return f"\033[92m{gmt_str}\033[0m"

def calculate_sun_times(lat, lon, tz_str, date=None):
    """Calculate sunrise, sunset, and twilight times.

    Astral may raise a ValueError when dawn/dusk do not exist (e.g. polar day/night).
    This function is resilient: it will try adjacent dates for sunrise/sunset and
    will return None for civil twilight if it cannot be computed.
    """
    if date is None:
        date = datetime.now().date()

    # Create location info
    location = LocationInfo("Airport", "Region", timezone=tz_str, latitude=lat, longitude=lon)

    def _try_adjacent_dates(fn):
        """Try to compute a sun time for the requested date, falling back to adjacent dates."""
        for d in (date, date - timedelta(days=1), date + timedelta(days=1)):
            try:
                return fn(location.observer, date=d, tzinfo=tz_str)
            except ValueError:
                continue
        # If we fall through, there was no valid time on any of the checked dates.
        raise

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
    """Parse a date string (YYYY-MM-DD or MM-DD) and return a date object."""
    date_input = date_input.strip()
    if not date_input:
        return datetime.now().date()

    if "-" in date_input:
        parts = date_input.split("-")
    elif "/" in date_input:
        parts = date_input.split("/")
    else:
        raise ValueError("Invalid date format. Use YYYY-MM-DD or MM-DD.")

    if len(parts) == 2:
        month, day = map(int, parts)
        year = datetime.now().year
    elif len(parts) == 3:
        year, month, day = map(int, parts)
    else:
        raise ValueError("Unexpected number of date parts.")

    return datetime(year, month, day).date()


def build_logging_night_url(airport: str, date: datetime):
    """Build a URL for logging night data to a Google Form."""
    url = f"https://loggingnight.org/?airport={airport}&date={date.year}-{date.month:02d}-{date.day:02d}"
    return url


def display_airport_info(
    airport_data: AirportData,
    iata_code: str,
    date=None,
    show_twilight: bool = True,
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
        sun_times = calculate_sun_times(lat, lon, tz_str, date)

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
        print(f"Airport: {iata_code} - {name}")
        print(f"Timezone: {tz_str} -> {tz_abbrev} ({gmt_offset}) for {date_note}")
        print(f"Logging Night URL: {build_logging_night_url(iata_code, datetime(date_note.year, date_note.month, date_note.day))}")
        print()
        # Only show civil twilight if requested and both dawn and dusk are available
        if show_twilight and civil_dawn and civil_dusk:
            print(f"Civil Twilight Begin:    {civil_dawn.strftime('%H:%M %Z')} ({format_gmt_time(civil_dawn)})    ->    Civil Twilight End:    {civil_dusk.strftime('%H:%M %Z')} ({format_gmt_time(civil_dusk)})")
        # print(f"Sunrise:               {sunrise.strftime('%H:%M:%S %Z')} ({sunrise.astimezone(pytz.UTC).strftime('%H:%M:%S GMT')})")
        print(f"1 Hour Before Sunrise:   {one_hr_before_sunrise.strftime('%H:%M %Z')} ({format_gmt_time(one_hr_before_sunrise)}){sunrise_note}    ->    1 Hour After Sunset:   {one_hr_after_sunset.strftime('%H:%M %Z')} ({format_gmt_time(one_hr_after_sunset)}){sunset_note}")
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
        help="Date to use (YYYY-MM-DD or MM-DD, current year assumed if omitted).",
    )
    parser.add_argument(
        "-nt",
        "--No-Twilight",
        dest="no_twilight",
        action="store_true",
        help="Do not display civil twilight (dawn/dusk) times.",
    )
    args = parser.parse_args()

    show_twilight = not args.no_twilight

    print("Airport Timezone and Dawn/Sunrise Information")
    print("-" * 60)

    airport_data = AirportData()
    if not airport_data.fetch_airport_data():
        return

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
            if display_airport_info(airport_data, airport, date_obj, show_twilight=show_twilight):
                successful += 1

        print()
        print(f"Processed {successful}/{len(airports)} airports successfully")
        return

    while True:
        # Get user input
        # Ask for date first (unless given on command line)
        if date_obj is None:
            date_input = input(
                "\nEnter a date (YYYY-MM-DD or MM-DD) or leave blank for today (or type 'q' to quit): "
            ).strip()
            if date_input.lower() in ("q", "quit", "exit"):
                break

            if date_input:
                try:
                    date_obj = parse_date(date_input)
                except ValueError:
                    print("Invalid date format. Please use YYYY-MM-DD or MM-DD.")
                    continue
            else:
                date_obj = datetime.now().date()
        else:
            # Use date provided via args for all iterations
            print(f"Using date: {date_obj}")

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
            if display_airport_info(airport_data, airport.strip(), date_obj, show_twilight=show_twilight):
                successful += 1

        print()
        print(f"Processed {successful}/{len(airports)} airports successfully")

        again = input("\nPress Enter to run again, or type 'q' to quit: ").strip().lower()
        if again in ("q", "quit", "exit"):
            break

        # Reset date selection each iteration unless it was provided on the command-line
        if args.date is None:
            date_obj = None

if __name__ == "__main__":
    main()
