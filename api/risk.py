from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt

# Risk score is ordinal for ranking only; the official route tie-breakers are applied first.
RISK_SCORE = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3, "No Travel": 4}

def classify(value, thresholds, no_travel=None):
    if value is None:
        return "Unavailable"
    if no_travel is not None and value >= no_travel:
        return "No Travel"
    if value < thresholds[0]:
        return "Low"
    if value < thresholds[1]:
        return "Moderate"
    if value < thresholds[2]:
        return "High"
    return "Severe"

def checkpoint_risk(wind_mph, rain_in_hr, snow_in_hr, load_weight_lb):
    # Assessment table: wind <25 / 25-34 / 35-44 / 45-54 / >=55
    wind = classify(wind_mph, (25, 35, 45), no_travel=55)
    rain = classify(rain_in_hr, (0.10, 0.25, 0.50))
    if rain_in_hr is not None and rain_in_hr > 1.00:
        rain = "No Travel"
    snow = classify(snow_in_hr, (0.5, 1.0, 2.0))
    if snow_in_hr is not None and snow_in_hr > 3.0:
        snow = "No Travel"

    # Load overrides from the assessment.
    if wind_mph is not None:
        if wind_mph >= 55:
            wind = "No Travel"
        elif 45 <= wind_mph < 55 and load_weight_lb > 30000:
            wind = "No Travel"
        elif 35 <= wind_mph < 45 and load_weight_lb > 40000:
            wind = "Severe"

    risks = [wind, rain, snow]
    rank = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3, "No Travel": 4, "Unavailable": -1}
    usable = [r for r in risks if r != "Unavailable"]
    overall = max(usable, key=lambda r: rank[r]) if usable else "Unavailable"
    return {"wind_risk": wind, "rain_risk": rain, "snow_risk": snow, "risk": overall,
            "risk_score": RISK_SCORE.get(overall, 0)}

def haversine_miles(a, b):
    # a and b are [longitude, latitude]
    lon1, lat1, lon2, lat2 = map(radians, [a[0], a[1], b[0], b[1]])
    dlon, dlat = lon2-lon1, lat2-lat1
    h = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 3958.8 * 2 * asin(sqrt(h))

def line_distances(coords):
    cumulative = [0.0]
    for i in range(1, len(coords)):
        cumulative.append(cumulative[-1] + haversine_miles(coords[i-1], coords[i]))
    return cumulative

def point_at_distance(coords, cumulative, target):
    if target <= 0:
        return coords[0]
    if target >= cumulative[-1]:
        return coords[-1]
    for i in range(1, len(cumulative)):
        if cumulative[i] >= target:
            span = cumulative[i] - cumulative[i-1]
            ratio = 0 if span == 0 else (target - cumulative[i-1]) / span
            return [coords[i-1][0] + (coords[i][0]-coords[i-1][0])*ratio,
                    coords[i-1][1] + (coords[i][1]-coords[i-1][1])*ratio]
    return coords[-1]
