# Spotter Weather-Aware Truck Routing — Backend

Django API for analyzing truck routes using weather forecasts, load weight, checkpoint risk, and travel time.

---

## ✨ What the Backend Does

- **Geocoding:** Converts origin and destination names into coordinates.
- **Route alternatives:** Requests available routes from a routing provider.
- **Weather checkpoints:** Samples weather along each route at the selected interval.
- **ETA-aware forecasts:** Estimates when the truck reaches each checkpoint and uses that time for the weather lookup.
- **Risk assessment:** Applies weather thresholds and load-weight overrides.
- **Route recommendation:** Ranks routes by severe-risk miles, high-risk miles, average risk, and travel time.
- **API response:** Returns route geometry, checkpoints, weather/risk information, route metrics, and the recommendation to the frontend.

> **Important:** This backend is responsible for the route, weather, risk, and recommendation calculations. The React frontend displays the results.

## 🧰 Requirements

- Python version compatible with the installed Django release
- `pip`
- Git (if cloning the repository)

## 🚀 Run Locally

Run these commands from the backend repository root — the directory containing `manage.py` and `requirements.txt`.

### 1. Create a virtual environment

**Windows PowerShell**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**
```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux / Git Bash**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The deployment requirements should include the dependencies used by the project, including Django, `django-cors-headers`, `requests`, and `gunicorn`.

### 3. Check the Django project

```bash
python manage.py check
```

If your project uses database migrations, run:

```bash
python manage.py migrate
```

### 4. Start the development server

```bash
python manage.py runserver 127.0.0.1:8000
```

Expected local endpoints:

- **Health check:** `http://127.0.0.1:8000/api/health/`
- **Trip analysis:** `http://127.0.0.1:8000/api/analyze/`

Check `config/urls.py` and `api/urls.py` if the actual URL paths in your code are different. The analysis endpoint is expected to accept a JSON `POST` request.

## 🔄 How the Backend Flow Works

1. **Receive trip details** — origin, destination, departure date/time, load weight, and checkpoint interval.
2. **Geocode locations** — convert place names into latitude/longitude coordinates.
3. **Request routes** — ask the routing provider for available route alternatives.
4. **Create checkpoints** — sample points along each route at the chosen distance interval.
5. **Estimate checkpoint ETA** — use the departure time and estimated route progress.
6. **Fetch forecast weather** — request weather for each checkpoint at the estimated arrival time.
7. **Calculate risk** — apply weather thresholds and load-weight overrides.
8. **Rank routes** — compare severe-risk miles, high-risk miles, average risk, and travel time in that order.
9. **Return results** — send route geometry, checkpoint details, metrics, and the recommendation as JSON.

## 🌦️ Weather Risk Rules

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---:|---:|---:|---:|---:|
| **Wind** | `<25 mph` | `25–34 mph` | `35–44 mph` | `45–54 mph` | `≥55 mph` |
| **Rain** | `<0.10 in/hr` | `0.10–0.25` | `0.25–0.50` | `0.50–1.00` | `>1.00 in/hr` |
| **Snow** | `<0.5 in/hr` | `0.5–1.0` | `1.0–2.0` | `2.0–3.0` | `>3.0 in/hr` |

### Load-weight overrides

- **Wind ≥55 mph:** No Travel for any load.
- **Wind 45–54 mph + load >30,000 lb:** No Travel.
- **Wind 35–44 mph + load >40,000 lb:** Severe.

> Make sure the implementation follows the assessment's boundary conditions exactly. Weather APIs may return metric units or accumulated precipitation, so confirm conversions and hourly-rate calculations in the code.

## 🏆 Route Recommendation

Routes are compared in this priority order:

1. **Fewest Severe-risk miles**
2. **Fewest High-risk miles**
3. **Lowest average risk**
4. **Shortest travel time**

This is a priority-based comparison. A faster route should not outrank another route if it has more severe-risk miles.

## 🌐 External Services

The implementation may use public services such as:

- **Nominatim** for geocoding
- **OSRM** for route alternatives and route geometry
- **Open-Meteo** for weather forecasts

These services can have usage limits, availability issues, and forecast-horizon limitations. Follow each provider's usage policy, especially for production traffic.

## ☁️ Deploy on Render

For a separate backend repository where `manage.py` and `requirements.txt` are at the repository root, use these typical settings:

| Setting | Value |
|---|---|
| **Root Directory** | Leave empty |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |

Ensure `gunicorn` is listed in `requirements.txt`.

Configure production settings securely:

- Set a strong `SECRET_KEY` using an environment variable.
- Set `DEBUG=False` in production.
- Add the deployed Render hostname to `ALLOWED_HOSTS`.
- Allow the deployed frontend URL in Django CORS settings.
- Do not commit secret values to GitHub.

After deployment, test the health endpoint and then submit a trip through the hosted frontend.

## 🛠️ Troubleshooting

| Problem | What to check |
|---|---|
| `gunicorn: command not found` | Add `gunicorn` to `requirements.txt`, commit/push, and redeploy. |
| CORS error in browser | Allow the exact frontend origin in Django CORS settings and redeploy. |
| `DisallowedHost` | Add the Render service hostname to `ALLOWED_HOSTS`. |
| `ModuleNotFoundError` | Confirm the missing package is in `requirements.txt` and installed in the build logs. |
| Routing or weather request fails | Check backend logs, provider availability, and request limits. |
| Fewer than three routes returned | The routing provider may return fewer alternatives for some trips. |
| No forecast for a checkpoint ETA | The provider may not cover that location/time; show missing data clearly instead of treating it as safe. |

## 📁 Main Project Structure

```text
backend/
├── api/              # API views, URL routes, risk and checkpoint logic
├── config/           # Django settings, URL and WSGI configuration
├── manage.py         # Django command-line entry point
├── requirements.txt  # Python dependencies
└── README.md         # Backend setup and project guide
```

## ⚠️ Safety Note

This application supports route planning; it does **not** guarantee road safety. Forecasts can change and public data may be incomplete. Drivers and dispatchers should follow official weather alerts, road closures, company policies, and applicable regulations.
