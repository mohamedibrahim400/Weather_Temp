# Task 1 — Weather Dashboard Website (Flask)

## What it does
- Detects user location in the browser (Geolocation API) and fetches current weather.
- If location detection fails, lets the user search by city.
- Shows temperature, humidity, wind speed, and a human-friendly description.
- Handles common errors (location blocked, network/API errors) with a visible banner.

## Tech
- Backend: Python `Flask`
- Weather + Geocoding API: Open-Meteo (free, no API key required)

## Run locally (Python 3.13 + venv)
From the repository root:

```bash
cd nagwa
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python .\task1_weather_dashboard\app.py
```

Open `http://127.0.0.1:5000/` in your browser.

## Notes
- If your browser blocks geolocation, use the city input section to fetch weather by city name.
- The backend endpoints are:
  - `GET /api/weather?lat=...&lon=...`
  - `GET /api/geocode?city=...`




--------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Task 2 — Log File Analyzer (CLI)

## What it does
- Parses Apache/Nginx-style access logs.
- Outputs:
  - Total requests
  - Unique IPs
  - Most common endpoints
  - Status code breakdown
- Flags potential issues:
  - High 4xx/5xx error rate
  - Suspicious IP activity (high volume, high error rate, sensitive endpoints)
- Prints a readable console summary and writes a JSON report.

## Run (Python 3.13 + venv)
From the repository root:

```bash
cd nagwa
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python .\task2_log_analyzer\log_analyzer.py .\access.log --out report.json
```

## Quick demo (no input file needed)
```bash
python .\task2_log_analyzer\log_analyzer.py --demo --out report.json
```

## Common Windows path tips
- If your file path contains spaces, wrap it in quotes: `python .\task2_log_analyzer\log_analyzer.py "C:\Logs\access log.txt"`
- The example `path\to\access.log` is a placeholder; replace it with a real path.

## Read from stdin (no file needed)
```bash
python .\task2_log_analyzer\log_analyzer.py - --out report.json
```
Then paste log lines and press `Ctrl+Z` then `Enter` (Windows) to end input.

## Options
- `--top 15` to include more endpoints
- `--error-threshold 0.2` to change high-error flagging
