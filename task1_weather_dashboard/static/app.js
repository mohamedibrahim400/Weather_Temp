const bannerEl = document.getElementById("banner");
const cityFallbackEl = document.getElementById("cityFallback");
const cityInputEl = document.getElementById("cityInput");
const cityResultsEl = document.getElementById("cityResults");

const locationLabelEl = document.getElementById("locationLabel");
const descriptionEl = document.getElementById("description");
const temperatureEl = document.getElementById("temperature");
const humidityEl = document.getElementById("humidity");
const windEl = document.getElementById("wind");
const statusEl = document.getElementById("status");

const refreshBtnEl = document.getElementById("refreshBtn");
const searchCityBtnEl = document.getElementById("searchCityBtn");

let lastKnownLocation = null;

function showBanner(message) {
  bannerEl.textContent = message;
  bannerEl.classList.remove("banner--hidden");
}

function hideBanner() {
  bannerEl.textContent = "";
  bannerEl.classList.add("banner--hidden");
}

function setStatus(text) {
  statusEl.textContent = text;
}

function setWeatherUI({ temperature_c, humidity_percent, wind_speed_kmh, description, location }) {
  descriptionEl.textContent = description ?? "—";
  temperatureEl.textContent = temperature_c != null ? Math.round(temperature_c).toString() : "—";
  humidityEl.textContent = humidity_percent != null ? `${Math.round(humidity_percent)}%` : "—";
  windEl.textContent = wind_speed_kmh != null ? `${Math.round(wind_speed_kmh)} km/h` : "—";

  if (location?.label) {
    locationLabelEl.textContent = `Location: ${location.label}`;
  } else if (location?.lat != null && location?.lon != null) {
    locationLabelEl.textContent = `Location: ${location.lat.toFixed(3)}, ${location.lon.toFixed(3)}`;
  } else {
    locationLabelEl.textContent = "Location";
  }
}

async function fetchWeatherByLatLon(lat, lon, label = null) {
  setStatus("Fetching weather…");
  hideBanner();

  const url = `/api/weather?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
  const res = await fetch(url);
  const data = await res.json();

  if (!res.ok || !data.ok) {
    throw new Error(data.error || "Failed to fetch weather.");
  }

  lastKnownLocation = { lat, lon, label };
  setWeatherUI({ ...data, location: { ...data.location, label } });
  setStatus("Updated");
}

function showCityFallback(message) {
  cityFallbackEl.classList.remove("card--hidden");
  if (message) showBanner(message);
}

function clearCityResults() {
  cityResultsEl.innerHTML = "";
}

function renderCityResult(result) {
  const row = document.createElement("div");
  row.className = "result";

  const left = document.createElement("div");
  const title = document.createElement("div");
  title.textContent = result.name ?? "Unknown place";
  const meta = document.createElement("div");
  meta.className = "result__meta";
  const parts = [result.admin1, result.country].filter(Boolean);
  meta.textContent = parts.join(" • ");
  left.appendChild(title);
  left.appendChild(meta);

  const btn = document.createElement("button");
  btn.className = "button button--ghost";
  btn.type = "button";
  btn.textContent = "Use";
  btn.addEventListener("click", async () => {
    try {
      clearCityResults();
      await fetchWeatherByLatLon(result.lat, result.lon, `${result.name}${parts.length ? ", " + parts.join(", ") : ""}`);
    } catch (err) {
      showBanner(err.message || "Failed to fetch weather for city.");
      setStatus("Error");
    }
  });

  row.appendChild(left);
  row.appendChild(btn);
  return row;
}

async function searchCity(city) {
  setStatus("Searching city…");
  hideBanner();
  clearCityResults();

  const url = `/api/geocode?city=${encodeURIComponent(city)}`;
  const res = await fetch(url);
  const data = await res.json();

  if (!res.ok || !data.ok) {
    throw new Error(data.error || "Failed to geocode the city.");
  }

  if (!data.results || data.results.length === 0) {
    cityResultsEl.textContent = "No matches found. Try a different city name.";
    setStatus("Ready");
    return;
  }

  for (const r of data.results) {
    cityResultsEl.appendChild(renderCityResult(r));
  }
  setStatus("Select a result");
}

async function detectLocationAndFetchWeather() {
  setStatus("Detecting location…");
  hideBanner();

  if (!navigator.geolocation) {
    showCityFallback("Geolocation is not supported by your browser. Enter a city instead.");
    setStatus("Ready");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      try {
        cityFallbackEl.classList.add("card--hidden");
        await fetchWeatherByLatLon(pos.coords.latitude, pos.coords.longitude);
      } catch (err) {
        showCityFallback(err.message || "Failed to fetch weather for your location.");
        setStatus("Error");
      }
    },
    () => {
      showCityFallback("Couldn’t detect your location. Enter a city instead.");
      setStatus("Ready");
    },
    { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }
  );
}

refreshBtnEl.addEventListener("click", async () => {
  try {
    if (lastKnownLocation) {
      await fetchWeatherByLatLon(lastKnownLocation.lat, lastKnownLocation.lon, lastKnownLocation.label);
    } else {
      await detectLocationAndFetchWeather();
    }
  } catch (err) {
    showBanner(err.message || "Refresh failed.");
    setStatus("Error");
  }
});

searchCityBtnEl.addEventListener("click", async () => {
  try {
    const city = (cityInputEl.value || "").trim();
    if (!city) {
      showBanner("Please enter a city name.");
      return;
    }
    await searchCity(city);
  } catch (err) {
    showBanner(err.message || "City search failed.");
    setStatus("Error");
  }
});

cityInputEl.addEventListener("keydown", async (e) => {
  if (e.key === "Enter") {
    searchCityBtnEl.click();
  }
});

detectLocationAndFetchWeather();

