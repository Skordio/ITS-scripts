"""
Script to calculate driving distances between airports.
Requires: tz_ez (for airport lookup data)
"""

import argparse
import os
import sys
import re
import math
import urllib.parse

# Ensure the workspace root is on sys.path so we can import tz_ez when running as a script.
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from lib_tz_ez.airport_data import AirportData


# The AirportData class replaces the old global cache and fetch logic.
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.
    Returns distance in miles.
    """
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    # Approximate driving distance as 1.25x the straight-line distance
    driving_distance = distance * 1.25
    
    return distance, driving_distance

def estimate_flight_time(distance_miles):
    """
    Estimate flight time in hours and minutes.
    Assumes average commercial jet speed of 550 mph, plus 30 minutes for takeoff/landing.
    """
    # Average speed: 550 mph
    # Add 30 minutes (0.5 hours) for takeoff and landing
    flight_hours = distance_miles / 550 + 0.5
    hours = int(flight_hours)
    minutes = int((flight_hours - hours) * 60)
    return hours, minutes

def display_airport_distances(airport_data: AirportData, airport_codes):
    """Calculate and display driving distances between all pairs of airports."""
    if len(airport_codes) < 2:
        print("✗ Please enter at least 2 airport codes to calculate distances.")
        return False

    # Get coordinates for all airports
    airports = {}
    for code in airport_codes:
        info = airport_data.get_airport_info(code.strip())
        if not info:
            print(f"⚠️ Airport {code} not found in database; distances will be omitted but a Google Maps link will still be provided.")
            airports[code.upper()] = {"name": code.upper(), "lat": None, "lon": None, "missing": True}
            continue
        lat, lon, name = info
        airports[code.upper()] = {"name": name, "lat": lat, "lon": lon, "missing": False}
    
    # Display results
    print(f"\n{'='*80}")
    print("Driving Distances Between Airports")
    print(f"{'='*80}\n")
    
    codes_list = list(airports.keys())
    
    # Calculate and display pairwise distances
    for i in range(len(codes_list)):
        for j in range(i + 1, len(codes_list)):
            code1 = codes_list[i]
            code2 = codes_list[j]
            
            airport1 = airports[code1]
            airport2 = airports[code2]
            
            print(f"{code1} ({airport1['name']}) <-> {code2} ({airport2['name']})")

            if airport1.get("missing") or airport2.get("missing"):
                print("    (Skipping distance calculation because airport coordinate data is missing.)")
            else:
                distance, driving_distance = haversine_distance(
                    airport1["lat"], airport1["lon"],
                    airport2["lat"], airport2["lon"]
                )

                flight_hours, flight_minutes = estimate_flight_time(distance)

                print(f"    Straight-line Distance: {distance:.1f} miles ({distance * 1.609:.1f} km)")
                print(f"    Estimated Driving Distance: {driving_distance:.1f} miles ({driving_distance * 1.609:.1f} km)")
                print(f"    Estimated Flight Time: {flight_hours}h {flight_minutes}m")

            print()
            maps_query = f"{code1} airport to {code2} airport"
            maps_url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(maps_query)
            print(f"For a more accurate driving route, open this Google Maps link:\n{maps_url}")
    
    print(f"{'='*80}")
    print("Note: Distances are estimated based on great-circle distance × 1.25")
    print("      Flight times assume 550 mph average speed + 30 min for takeoff/landing")
    print("      For actual driving routes, use Google Maps or a routing service.")
    print("      For actual flight times, check airline schedules.")
    
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Airport Driving Distance Calculator (uses OpenFlights airport database)"
    )
    parser.add_argument(
        "-a",
        "--airport",
        "--airports",
        nargs="+",
        help="Airport codes (IATA 3-letter or ICAO 4-letter) to calculate distances between.",
    )
    args = parser.parse_args()

    print("Airport Driving Distance Calculator")
    print("-" * 60)

    airport_data = AirportData()
    if not airport_data.fetch_airport_data():
        return

    if args.airport:
        airports = [a.strip() for a in args.airport if a.strip()]
        if not airports:
            print("✗ No airport codes provided.")
            return
        display_airport_distances(airport_data, airports)
        return

    # Ignore non-letter characters
    try:
        airports = airport_data.prompt_airports_from_user()
    except KeyboardInterrupt:
        print("\nExiting.")
        return

    if not airports:
        print("No airports entered. Exiting.")
        return

    # Display distances
    display_airport_distances(airport_data, airports)

if __name__ == "__main__":
    main()
