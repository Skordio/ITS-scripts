# ITS Scripts

A collection of aviation utility scripts and browser extensions for timezone lookups, sunrise/sunset times, airport distances, and time conversions.

---

## Tools

| Tool | Type | Description |
|------|------|-------------|
| [lib_tz_ez](#lib_tz_ez) | Python CLI | Timezone, sunrise/sunset, and ADS-B info for airports |
| [lib_drive_dist](#lib_drive_dist) | Python CLI | Great-circle and estimated driving distance between airports |
| [time_difference_calc](#time_difference_calc) | Python GUI | Simple military-time duration calculator |
| [edge-time-converter](#edge-time-converter) | Browser extension | Auto-converts times on web pages to GMT |

---

## Setup

All Python tools share a virtual environment. The PowerShell wrapper scripts handle environment setup automatically:

```powershell
# First run: creates .venv and installs requirements.txt
./tz_ez.ps1
```

To set up manually:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

---

## lib_tz_ez

Displays timezone, sunrise/sunset, and civil twilight times for one or more airports. Optionally generates links to [loggingnight.org](https://loggingnight.org) and [ADS-B Exchange](https://globe.adsbexchange.com) for a given flight.

### Usage

```powershell
./tz_ez.ps1 [arguments]
```

```bash
python programs/lib_tz_ez/run.py [arguments]
```

Run with no arguments to enter interactive mode.

### Arguments

| Argument | Description |
|----------|-------------|
| `-a, --airport CODES` | One or more airport codes (IATA 3-letter or ICAO 4-letter), e.g. `SXM TNCM` |
| `-d, --date DATE` | Date as `MM-DD-YYYY` or `MM-DD` (defaults to today) |
| `-c, --aircraft NNUM` | Aircraft N-number (e.g. `N971MC`) — generates an ADS-B Exchange URL |
| `-o, --open-adsb` | Open ADS-B Exchange link(s) in the browser instead of printing them |
| `-nt, --No-Twilight` | Hide civil twilight (dawn/dusk) times |
| `--sun-search-window-days N` | Days before/after the date to search for sunrise/sunset when none is found (default: `1`) |
| `--save-defaults` | Save the current arguments as defaults for future runs |
| `--clear-defaults` | Clear all saved defaults |

### Examples

```powershell
# Interactive mode
./tz_ez.ps1

# Single airport, today
./tz_ez.ps1 -a SXM

# Multiple airports, specific date
./tz_ez.ps1 -a SXM TNCM -d 04-03-2026

# With aircraft — prints loggingnight.org and ADS-B Exchange URLs
./tz_ez.ps1 -a SXM -d 04-03-2026 -c N971MC

# Open ADS-B link automatically in browser
./tz_ez.ps1 -a SXM -d 04-03-2026 -c N971MC -o

# Save -c and -o as defaults so you never have to type them again
./tz_ez.ps1 -c N971MC -o --save-defaults

# Reset saved defaults
./tz_ez.ps1 --clear-defaults
```

### Output

```
============================================================
Airport: SXM - Princess Juliana International Airport
Timezone: America/Lower_Princes -> AST (GMT-4) for 2026-04-03
Logging Night URL: https://loggingnight.org/?airport=SXM&date=2026-04-03
ADS-B Exchange URL: https://globe.adsbexchange.com/?icao=ad8872&lat=18.041&lon=-63.109&zoom=9.0&showTrace=2026-04-03

 Civil Twilight Begin:   05:58 AST (09:58 GMT)  ->  (22:43 GMT) 18:43 AST  :Civil Twilight End
1 Hour Before Sunrise:   06:22 AST (10:22 GMT)  ->  (22:18 GMT) 18:18 AST  :1 Hour After Sunset
```

### Defaults

`--save-defaults` saves your preferences to `programs/lib_tz_ez/user_defaults.json`. On future runs these are applied automatically. `date` and `airport` are never saved (they change per flight). Everything else — `aircraft`, `open_adsb`, `no_twilight`, `sun_search_window_days` — can be saved.

### User Airport Overrides

If an airport code isn't found in the OpenFlights database, the tool will offer to let you add it manually. Custom airports are stored in `programs/lib_tz_ez/user_airports.csv` and persist across runs.

### ADS-B Exchange / FAA Registry

When `-c` is provided, the tool looks up the exact ICAO Mode S hex address from the FAA releasable aircraft registry. The registry (~20 MB) is downloaded on first use and cached locally for 30 days (`programs/lib_tz_ez/faa_registry_icao.csv`).

---

## lib_drive_dist

Calculates great-circle distance and estimated driving distance between any combination of airports, plus estimated flight time and a Google Maps link for each pair.

### Usage

```powershell
./drive_dist.ps1 [arguments]
```

```bash
python programs/lib_drive_dist/run.py [arguments]
```

Run with no arguments to enter interactive mode.

### Arguments

| Argument | Description |
|----------|-------------|
| `-a, --airport CODES` | Two or more airport codes (IATA or ICAO) |

### Example

```powershell
./drive_dist.ps1 -a JFK LAX ORD
```

### Output

For each pair of airports:
- Straight-line distance (miles and km)
- Estimated driving distance (straight-line × 1.25)
- Estimated flight time (at 550 mph average + 30 min overhead)
- Google Maps directions link

---

## time_difference_calc

A small Tkinter GUI for calculating the duration between two times in 24-hour (military) format.

### Usage

```powershell
./time_difference_calc.ps1
```

```bash
python programs/time_difference_calc.py
```

Enter a start time and end time (e.g. `0830`, `14:22`). The tool handles overnight spans automatically (if end time is earlier than start time, it assumes the next day).

---

## edge-time-converter

A Chromium browser extension (tested on Edge, compatible with Chrome) that automatically converts times found on web pages to their GMT equivalent.

**Example:** `10:28AM MDT` → `16:28 GMT`

### Installation

1. Open `edge://extensions` (or `chrome://extensions`)
2. Enable **Developer mode**
3. Click **Load unpacked** and select the `edge-time-converter/` folder

### Features

- Toggle conversion on/off per tab via the extension popup
- Handles 40+ timezone abbreviations across North America, Europe, Asia, Pacific, and more
- Watches for dynamically loaded content (e.g. single-page apps)
- **loggingnight.org special support:** automatically derives the correct timezone from the page's state and date metadata, since times there don't include timezone labels
- Restores original page text when toggled off
- State resets when the browser closes (session storage)

### Supported Timezones

North America (EST/EDT, CST/CDT, MST/MDT, PST/PDT, AST/ADT, AKST/AKDT, HST, NST/NDT), Europe (GMT, UTC, WET/WEST, CET/CEST, EET/EEST, MSK), Asia/Pacific (IST, PKT, ICT, JST, KST, HKT, SGT, AWST, AEST/AEDT, ACST, NZST/NZDT), and more.

---

## Requirements

See `requirements.txt` for the full list. Key dependencies:

| Package | Purpose |
|---------|---------|
| `astral` | Sunrise/sunset/twilight calculations |
| `timezonefinder` | Timezone lookup from lat/lon coordinates |
| `pytz` | Timezone conversion |
| `requests` | HTTP requests (airport database, FAA registry) |
| `icao-nnumber-converter-us` | FAA N-number ↔ ICAO Mode S hex conversion |
