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

