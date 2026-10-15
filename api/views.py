import json
import traceback
from datetime import datetime, timedelta

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .risk import checkpoint_risk, line_distances, point_at_distance


# 1. CONFIGURATION

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

HEADERS = {
    "User-Agent": (
        "SpotterWeatherRoutingAssessment/1.0 "
        "(educational prototype)"
    )
}

ROUTE_NAMES = ["Route A", "Route B", "Route C"]

ALLOWED_CHECKPOINT_INTERVALS = (10, 25, 50)


# 2. HEALTH CHECK

def health(request):
    """Check whether the Django API is running."""

    return JsonResponse({
        "ok": True,
        "service": "spotter-weather-routing-api",
    })


# 3. LOCATION SERVICES

def geocode(place):
    """Convert a location name into longitude and latitude."""

    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": place,
            "format": "jsonv2",
            "limit": 1,
        },
        headers=HEADERS,
        timeout=15,
    )

    response.raise_for_status()

    locations = response.json()

    if not locations:
        raise ValueError(f"Could not find location: {place}")

    location = locations[0]

    coordinates = [
        float(location["lon"]),
        float(location["lat"]),
    ]

    label = location.get("display_name", place)

    return coordinates, label


# 4. WEATHER SERVICE

def weather_at(longitude, latitude, arrival_time):
    """
    Fetch hourly weather for a checkpoint.

    Select the forecast hour nearest to the checkpoint ETA.
    Return unavailable when no forecast is close enough.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m,rain,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "forecast_days": 7,
    }

    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()
    hourly = data.get("hourly", {})
    forecast_times = hourly.get("time", [])

    if not forecast_times:
        return {"weather_available": False}

    # Compare local timestamps without timezone information.
    target_time = arrival_time.replace(tzinfo=None)

    matching_times = []

    for index, forecast_time in enumerate(forecast_times):
        try:
            forecast_datetime = datetime.fromisoformat(
                forecast_time
            )

            difference = abs(
                (forecast_datetime - target_time).total_seconds()
            )

            matching_times.append(
                (difference, index, forecast_time)
            )

        except ValueError:
            continue

    if not matching_times:
        return {"weather_available": False}

    # Find the closest forecast hour.
    difference, index, selected_time = min(matching_times)

    difference_hours = difference / 3600

    # Do not use a forecast that is too far from the ETA.
    if difference_hours > 1.01:
        return {
            "weather_available": False,
            "weather_note": (
                "No hourly forecast near estimated arrival"
            ),
        }

    def get_weather_value(field):
        values = hourly.get(field, [])

        if index < len(values):
            return values[index]

        return None

    return {
        "weather_available": True,
        "weather_time": selected_time,
        "wind_mph": get_weather_value("wind_speed_10m"),
        "rain_in_hr": get_weather_value("rain"),
        "snow_in_hr": get_weather_value("snowfall"),
        "temperature_note": "Open-Meteo hourly forecast",
    }


# 5. CHECKPOINT PROCESSING

def get_checkpoint_distances(total_miles, interval):
    """Create checkpoint distances along the route."""

    distances = []
    distance = float(interval)

    while distance < total_miles:
        distances.append(distance)
        distance += float(interval)

    # Always include the destination.
    distances.append(total_miles)

    return distances


def build_checkpoints(route, departure, load, interval):
    """
    Build route checkpoints.

    For every checkpoint:
    1. Find its coordinates.
    2. Estimate its arrival time.
    3. Fetch weather.
    4. Calculate weather risk.
    """

    coordinates = route["geometry"]["coordinates"]

    cumulative_distances = line_distances(coordinates)

    total_miles = (
        cumulative_distances[-1]
        if cumulative_distances
        else 0
    )

    route_duration_seconds = route.get("duration", 0)

    checkpoint_distances = get_checkpoint_distances(
        total_miles,
        interval,
    )

    checkpoints = []

    for index, distance in enumerate(checkpoint_distances):
        # Find the checkpoint's geographic position.
        point = point_at_distance(
            coordinates,
            cumulative_distances,
            distance,
        )

        # Estimate ETA based on progress along the route geometry.
        progress = (
            distance / total_miles
            if total_miles > 0
            else 0
        )

        arrival_time = departure + timedelta(
            seconds=route_duration_seconds * progress
        )

        # Fetch weather for the estimated arrival time.
        try:
            weather = weather_at(
                point[0],
                point[1],
                arrival_time,
            )

        except requests.RequestException:
            weather = {
                "weather_available": False,
                "weather_note": (
                    "Weather provider temporarily unavailable"
                ),
            }

        # Calculate risk only when weather is available.
        if weather.get("weather_available"):
            risks = checkpoint_risk(
                weather.get("wind_mph"),
                weather.get("rain_in_hr"),
                weather.get("snow_in_hr"),
                load,
            )

        else:
            risks = {
                "wind_risk": "Unavailable",
                "rain_risk": "Unavailable",
                "snow_risk": "Unavailable",
                "risk": "Unavailable",
                "risk_score": 0,
            }

        checkpoint = {
            "index": index + 1,
            "miles_from_start": round(distance, 1),
            "coordinates": point,
            "eta": arrival_time.isoformat(timespec="minutes"),
            **weather,
            **risks,
        }

        checkpoints.append(checkpoint)

    return checkpoints, total_miles


# 6. ROUTE METRICS

def route_metrics(route, checkpoints):
    """Calculate the summary information for one route."""

    severe_miles = 0.0
    high_miles = 0.0

    total_risk_score = 0.0
    valid_risk_count = 0

    for index, checkpoint in enumerate(checkpoints):

        # Distance covered since the previous checkpoint.
        previous_distance = (
            checkpoints[index - 1]["miles_from_start"]
            if index > 0
            else 0.0
        )

        segment_miles = max(
            0.0,
            checkpoint["miles_from_start"] - previous_distance,
        )

        # Count miles affected by severe or high risk.
        if checkpoint["risk"] == "Severe":
            severe_miles += segment_miles

        if checkpoint["risk"] == "High":
            high_miles += segment_miles

        # Exclude unavailable weather from the average.
        if checkpoint["risk"] != "Unavailable":
            total_risk_score += checkpoint["risk_score"]
            valid_risk_count += 1

    average_risk = (
        round(total_risk_score / valid_risk_count, 2)
        if valid_risk_count
        else None
    )

    return {
        "severe_miles": round(severe_miles, 1),
        "high_miles": round(high_miles, 1),
        "average_risk": average_risk,
        "duration_minutes": round(
            route.get("duration", 0) / 60
        ),
        "distance_miles": round(
            route.get("distance", 0) / 1609.344,
            1,
        ),
        "no_travel": any(
            checkpoint["risk"] == "No Travel"
            for checkpoint in checkpoints
        ),
    }


# 7. INPUT VALIDATION

def validate_payload(payload):
    """Read and validate the trip details sent by the frontend."""

    origin = str(payload.get("origin", "")).strip()
    destination = str(payload.get("destination", "")).strip()
    departure_raw = str(
        payload.get("departure_time", "")
    ).strip()

    if not origin or not destination or not departure_raw:
        raise ValueError(
            "Origin, destination, and departure time are required."
        )

    load = float(payload.get("load_weight_lb", 0))
    interval = int(payload.get("checkpoint_miles", 25))
    forecast_offset = int(
        payload.get("forecast_offset_hours", 0)
    )

    if (
        load < 0
        or interval not in ALLOWED_CHECKPOINT_INTERVALS
        or not 0 <= forecast_offset <= 48
    ):
        raise ValueError(
            "Load must be non-negative; interval must be "
            "10, 25, or 50; forecast offset must be 0–48."
        )

    departure = datetime.fromisoformat(
        departure_raw
    ) + timedelta(hours=forecast_offset)

    return {
        "origin": origin,
        "destination": destination,
        "departure": departure,
        "load": load,
        "interval": interval,
    }


# 8. ROUTING SERVICE

def get_routes(start, end):
    """Request alternative driving routes from OSRM."""

    url = (
        f"{OSRM_URL}/"
        f"{start[0]},{start[1]};"
        f"{end[0]},{end[1]}"
    )

    response = requests.get(
        url,
        params={
            "alternatives": "2",
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingProviderError(
            "Routing provider did not return a route. "
            "Try more specific locations."
        )

    return data["routes"][:3]


class RoutingProviderError(Exception):
    """Raised when the routing provider returns no usable route."""


def analyze_route(route, index, departure, load, interval):
    """Build the checkpoints and summary for one route."""

    checkpoints, _ = build_checkpoints(
        route,
        departure,
        load,
        interval,
    )

    summary = route_metrics(route, checkpoints)

    return {
        "id": f"route-{index + 1}",
        "name": ROUTE_NAMES[index],
        "geometry": route["geometry"],
        "checkpoints": checkpoints,
        "summary": summary,
        "provider_distance_miles": summary["distance_miles"],
    }


def rank_routes(routes):
    """Rank routes using the assessment's priority order."""

    routes.sort(
        key=lambda route: (
            route["summary"]["severe_miles"],
            route["summary"]["high_miles"],
            (
                route["summary"]["average_risk"]
                if route["summary"]["average_risk"] is not None
                else 999
            ),
            route["summary"]["duration_minutes"],
        )
    )

    for index, route in enumerate(routes):
        route["rank"] = index + 1
        route["recommended"] = index == 0

    return routes


# 9. ANALYSIS RESPONSE

def create_analysis_response(
    origin_label,
    destination_label,
    start,
    end,
    departure,
    load,
    interval,
    routes,
):
    """Create the JSON response expected by the frontend."""

    return {
        "origin": {
            "label": origin_label,
            "coordinates": start,
        },
        "destination": {
            "label": destination_label,
            "coordinates": end,
        },
        "departure_time": departure.isoformat(timespec="minutes"),
        "load_weight_lb": load,
        "checkpoint_miles": interval,
        "routes": routes,
        "notice": (
            "Routing demo may provide fewer than three alternatives. "
            "Weather is an hourly forecast estimate at each checkpoint ETA."
        ),
    }


# 10. MAIN ANALYSIS API

@csrf_exempt
def analyze(request):
    """Analyze a trip and return routes, weather, and risk summaries."""

    if request.method != "POST":
        return JsonResponse(
            {"error": "Use POST."},
            status=405,
        )

    try:
        # Step 1: Read and validate the user's inputs.
        payload = json.loads(request.body or "{}")
        trip = validate_payload(payload)

        origin = trip["origin"]
        destination = trip["destination"]
        departure = trip["departure"]
        load = trip["load"]
        interval = trip["interval"]

        # Step 2: Convert locations into coordinates.
        start, origin_label = geocode(origin)
        end, destination_label = geocode(destination)

        # Step 3: Get the alternative driving routes.
        provider_routes = get_routes(start, end)

        # Step 4: Analyze every returned route.
        routes = []

        for index, route in enumerate(provider_routes):
            routes.append(
                analyze_route(
                    route,
                    index,
                    departure,
                    load,
                    interval,
                )
            )

        # Step 5: Rank routes and choose a recommendation.
        routes = rank_routes(routes)

        # Step 6: Return the response.
        response_data = create_analysis_response(
            origin_label,
            destination_label,
            start,
            end,
            departure,
            load,
            interval,
            routes,
        )

        return JsonResponse(response_data)

    except ValueError as error:
        return JsonResponse(
            {"error": str(error)},
            status=400,
        )

    except RoutingProviderError as error:
        return JsonResponse(
            {"error": str(error)},
            status=502,
        )

    except requests.RequestException as error:
        traceback.print_exc()

        return JsonResponse(
            {
                "error": (
                    "External API connection failed: "
                    f"{type(error).__name__}: {str(error)}"
                )
            },
            status=502,
        )

    except Exception as error:
        return JsonResponse(
            {
                "error": (
                    f"Unexpected analysis error: {str(error)}"
                )
            },
            status=500,
        )