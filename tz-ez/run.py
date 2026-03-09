"""
Script to fetch and display timezone and dawn/sunrise info for airports.
Requires: astral, timezonefinder, requests
Install with: pip install astral timezonefinder requests
"""

import requests
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
from timezonefinder import TimezoneFinder
import pytz
import io
import re
import csv

# Cache for airport data
_AIRPORT_CACHE = {}

def fetch_airport_data():
    """Fetch airport data from OpenFlights database on GitHub."""
    global _AIRPORT_CACHE
    
    if _AIRPORT_CACHE:
        return _AIRPORT_CACHE
    
    print("Fetching airport data from OpenFlights database...")
    
    try:
        # OpenFlights data: https://openflights.org/data.html
        # Format: Airport ID, Name, City, Country, IATA, ICAO, Latitude, Longitude, Altitude, Timezone, DST, Timezone (IANA)
        url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse the CSV data
        csv_reader = csv.reader(io.StringIO(response.text))
        for row in csv_reader:
            if len(row) >= 8:  # Ensure we have at least lat and lon
                try:
                    iata = row[4].strip()  # IATA code
                    icao = row[5].strip()  # ICAO code
                    name = row[1].strip()  # Airport name
                    lat = float(row[6])  # Latitude
                    lon = float(row[7])  # Longitude
                    
                    # Store airports with either IATA (3 letters) or ICAO (4 letters) codes
                    if iata and len(iata) == 3 and iata != '\\N':
                        _AIRPORT_CACHE[iata.upper()] = (lat, lon, name)
                    if icao and len(icao) == 4 and icao != '\\N':
                        _AIRPORT_CACHE[icao.upper()] = (lat, lon, name)
                except (ValueError, IndexError):
                    continue
        
        print(f"Successfully loaded {len(_AIRPORT_CACHE)} airports from OpenFlights database.\n")
        return _AIRPORT_CACHE
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching airport data: {e}")
        print("✗ Cannot proceed without airport data.")
        return None

def get_airport_info(iata_code):
    """Get latitude and longitude for an airport code."""
    iata_upper = iata_code.upper()
    if iata_upper in _AIRPORT_CACHE:
        return _AIRPORT_CACHE[iata_upper]
    
    # Try ICAO with K prefix for US airports if 3-letter code not found
    if len(iata_upper) == 3:
        icao_attempt = 'K' + iata_upper
        if icao_attempt in _AIRPORT_CACHE:
            return _AIRPORT_CACHE[icao_attempt]
    
    return None

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
    """Calculate sunrise, sunset, and twilight times."""
    if date is None:
        date = datetime.now().date()
    
    # Create location info
    location = LocationInfo("Airport", "Region", timezone=tz_str, latitude=lat, longitude=lon)
    
    # Get sun times (may include 'dawn' and 'dusk' for civil twilight).
    # Do NOT fall back to a fixed offset if dawn/dusk are missing — return
    # None so the caller can choose to omit displaying civil twilight.
    sun_times = sun(location.observer, date=date)

    dawn = sun_times.get("dawn")
    dusk = sun_times.get("dusk")

    return {
        "civil_twilight_begin": dawn,
        "civil_twilight_end": dusk,
        "sunrise": sun_times["sunrise"],
        "sunset": sun_times["sunset"],
    }

def display_airport_info(iata_code, date=None):
    """Fetch and display info for an airport on a given date."""
    airport_info = get_airport_info(iata_code)
    
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
        
        # Convert times to local timezone (only convert civil twilight if present)
        civil_dawn = None
        civil_dusk = None
        if sun_times.get("civil_twilight_begin"):
            civil_dawn = sun_times["civil_twilight_begin"].astimezone(tz)
        if sun_times.get("civil_twilight_end"):
            civil_dusk = sun_times["civil_twilight_end"].astimezone(tz)

        sunrise = sun_times.get("sunrise").astimezone(tz)
        sunset = sun_times.get("sunset").astimezone(tz)
        
        # Calculate 1 hour before/after sunrise
        one_hr_before_sunrise = sunrise - timedelta(hours=1)
        one_hr_after_sunset = sunset + timedelta(hours=1)
        
        # Display info
        print(f"\n{'='*60}")
        print(f"Airport: {iata_code} - {name}")
        print(f"Timezone: {tz_str}")
        print()
        # Only show civil twilight if both dawn and dusk are available
        if civil_dawn and civil_dusk:
            print(f"Civil Twilight Begin:    {civil_dawn.strftime('%H:%M %Z')} ({format_gmt_time(civil_dawn)})    ->    Civil Twilight End:    {civil_dusk.strftime('%H:%M %Z')} ({format_gmt_time(civil_dusk)})")
        # print(f"Sunrise:               {sunrise.strftime('%H:%M:%S %Z')} ({sunrise.astimezone(pytz.UTC).strftime('%H:%M:%S GMT')})")
        print(f"1 Hour Before Sunrise:   {one_hr_before_sunrise.strftime('%H:%M %Z')} ({format_gmt_time(one_hr_before_sunrise)})    ->    1 Hour After Sunset:   {one_hr_after_sunset.strftime('%H:%M %Z')} ({format_gmt_time(one_hr_after_sunset)})")
        # print(f"{'='*60}")
        # print("* GMT time is on a different day than the local time")
        
        return True
    
    except Exception as e:
        print(f"✗ Error processing {iata_code}: {e}")
        raise e
        return False

def main():
    """Main function."""
    print("Airport Timezone and Dawn/Sunrise Information")
    print("-" * 60)
    
    # Fetch airport data from internet
    airport_data = fetch_airport_data()
    if not airport_data:
        return
    
    # Get user input
    # Ask for date first
    date_input = input("\nEnter a date (YYYY-MM-DD) or leave blank for today: ").strip()
    if date_input:
        try:
            date_obj = datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
            return
    else:
        date_obj = None

    airport_list = input("\nEnter airport codes separated by spaces (IATA 3-letter or ICAO 4-letter codes, e.g., JFK KJFK LAX KLAX): ").strip()
    
    # Ignore non-letter characters
    airport_list = re.sub(r'[^a-zA-Z0-9\s]', ' ', airport_list)
    
    if not airport_list:
        print("No airports entered. Exiting.")
        return
    
    airports = airport_list.split()
    
    # Process each airport
    successful = 0
    for airport in airports:
        if display_airport_info(airport.strip(), date_obj):
            successful += 1
    
    print()
    print(f"Processed {successful}/{len(airports)} airports successfully")

if __name__ == "__main__":
    main()
