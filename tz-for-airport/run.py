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
        for line in response.text.strip().split('\n'):
            parts = [p.strip().strip('"') for p in line.split(',')]
            if len(parts) >= 7:
                try:
                    iata = parts[4]  # IATA code
                    name = parts[1]  # Airport name
                    lat = float(parts[6])  # Latitude
                    lon = float(parts[7])  # Longitude
                    
                    # Only store airports with IATA codes
                    if iata and len(iata) == 3:
                        _AIRPORT_CACHE[iata.upper()] = (lat, lon, name)
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
    return None

def get_timezone(lat, lon):
    """Get timezone string from coordinates."""
    tf = TimezoneFinder()
    return tf.timezone_at(lat=lat, lng=lon)

def calculate_sun_times(lat, lon, tz_str, date=None):
    """Calculate sunrise, sunset, and twilight times."""
    if date is None:
        date = datetime.now().date()
    
    # Create location info
    location = LocationInfo("Airport", "Region", timezone=tz_str, latitude=lat, longitude=lon)
    
    # Get sun times
    sun_times = sun(location.observer, date=date)
    
    return {
        "civil_twilight_begin": sun_times["civil_dawn"],
        "civil_twilight_end": sun_times["civil_dusk"],
        "sunrise": sun_times["sunrise"],
        "sunset": sun_times["sunset"],
    }

def display_airport_info(iata_code):
    """Fetch and display info for an airport."""
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
        
        # Get sun times
        sun_times = calculate_sun_times(lat, lon, tz_str)
        
        # Create timezone-aware datetimes
        tz = pytz.timezone(tz_str)
        
        # Convert times to local timezone
        civil_dawn = sun_times["civil_twilight_begin"].astimezone(tz)
        civil_dusk = sun_times["civil_twilight_end"].astimezone(tz)
        sunrise = sun_times["sunrise"].astimezone(tz)
        
        # Calculate 1 hour before/after sunrise
        one_hr_before_sunrise = sunrise - timedelta(hours=1)
        one_hr_after_sunrise = sunrise + timedelta(hours=1)
        
        # Display info
        print(f"\n{'='*60}")
        print(f"Airport: {iata_code} - {name}")
        print(f"Timezone: {tz_str}")
        print(f"{'='*60}")
        print(f"Civil Twilight Begin: {civil_dawn.strftime('%H:%M:%S')}")
        print(f"Civil Twilight End:   {civil_dusk.strftime('%H:%M:%S')}")
        print(f"Sunrise:              {sunrise.strftime('%H:%M:%S')}")
        print(f"1 Hour Before Sunrise: {one_hr_before_sunrise.strftime('%H:%M:%S')}")
        print(f"1 Hour After Sunrise:  {one_hr_after_sunrise.strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
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
    airport_list = input("\nEnter airport codes separated by spaces (e.g., JFK LAX ORD): ").strip()
    
    if not airport_list:
        print("No airports entered. Exiting.")
        return
    
    airports = airport_list.split()
    
    # Process each airport
    successful = 0
    for airport in airports:
        if display_airport_info(airport.strip()):
            successful += 1
    
    print(f"\n{'='*60}")
    print(f"Processed {successful}/{len(airports)} airports successfully")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
