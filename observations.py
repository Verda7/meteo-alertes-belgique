"""Observations METAR récentes à proximité de la localité choisie."""

from math import asin, cos, exp, isfinite, radians, sin, sqrt
import re

import pandas as pd
import requests
import streamlit as st

BELGIAN_STATIONS = 'EBAW,EBBE,EBBL,EBBR,EBCI,EBFS,EBKT,EBLG,EBOS'
METAR_URL = 'https://aviationweather.gov/api/data/metar'


@st.cache_data(ttl=600, show_spinner=False)
def belgian_reports():
    try:
        response = requests.get(METAR_URL, params={
            'ids': BELGIAN_STATIONS, 'format': 'json', 'hours': 2,
        }, timeout=4)
        response.raise_for_status()
        return response.json() if response.status_code != 204 else []
    except (requests.RequestException, ValueError):
        return []


def observed_weather(report):
    phenomena = report.get('wxString') or ''
    for pattern, code, description in (
        (r'TS', 95, 'Orage'),
        (r'FZ(?:RA|DZ)', 66, 'Précipitations verglaçantes'),
        (r'SN|SG', 73, 'Neige'),
        (r'PL|GR|GS', 77, 'Grésil ou grêle'),
        (r'RA', 61, 'Pluie'),
        (r'DZ', 51, 'Bruine'),
        (r'FG', 45, 'Brouillard'),
        (r'BR', 45, 'Brume'),
    ):
        if re.search(pattern, phenomena):
            return code, description
    if not phenomena:
        code = {
            'CLR': 0, 'SKC': 0, 'NCD': 0, 'FEW': 1,
            'SCT': 2, 'BKN': 2, 'OVC': 3,
        }.get(report.get('cover'))
        if code is not None:
            return code, None
    if not phenomena and report.get('cover') == 'CAVOK':
        return None, 'Bonne visibilité observée'
    return None


def nearby_observation(reports, latitude, longitude, now):
    candidates = []
    for report in reports:
        try:
            observed_at = pd.Timestamp(report['obsTime'], unit='s', tz='UTC').tz_convert(now.tz)
            lat, lon = float(report['lat']), float(report['lon'])
            station = report['icaoId']
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if pd.isna(observed_at) or not pd.Timedelta(0) <= now - observed_at <= pd.Timedelta(minutes=75):
            continue
        distance = distance_km(latitude, longitude, lat, lon)
        if distance <= 15:
            candidates.append((distance, -observed_at.timestamp(), report, station, observed_at))
    if candidates:
        distance, _, report, station, observed_at = min(candidates, key=lambda value: value[:2])
        condition = observed_weather(report)
        if condition is not None:
            code, description = condition
            source = f'Observé à {station} · {distance:.0f} km · {observed_at:%H:%M}'
            if code is None:
                return None, None, f'Conditions prévues · {description.lower()} à {station} ({distance:.0f} km, {observed_at:%H:%M})'
            return code, description, source
    return None


def station_feel(temp, report):
    wind_chill = report.get('windchill')
    if wind_chill is not None and isfinite(float(wind_chill)):
        return float(wind_chill) - 273.15, ''
    humidity, wind = report.get('humidity'), report.get('wind_speed')
    value = apparent_temperature(temp, humidity, wind)
    return value, 'Calculé à partir des relevés de Rèves' if value is not None else ''


def apparent_temperature(temp, humidity, wind):
    if humidity is None or wind is None:
        return None
    try:
        humidity, wind = float(humidity), float(wind)
        if 0 <= humidity <= 100 and isfinite(wind) and wind >= 0:
            vapor_pressure = humidity / 100 * 6.105 * exp(17.27 * temp / (237.7 + temp))
            return temp + 0.33 * vapor_pressure - 0.70 * wind - 4.00
    except (TypeError, ValueError, OverflowError, ZeroDivisionError):
        pass
    return None


def charleroi_feel(reports, temp, humidity, measured_at, now):
    """Estimate apparent temperature using nearby observed sustained wind."""
    candidates = []
    for report in reports:
        if report.get('icaoId') != 'EBCI':
            continue
        try:
            time = pd.Timestamp(report['obsTime'], unit='s', tz='UTC')
            speed = float(report['wspd'])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not (isfinite(speed) and speed >= 0 and speed != 999):
            continue
        delta = abs(time - measured_at)
        if pd.Timedelta(0) <= now - time <= pd.Timedelta(minutes=45) and delta <= pd.Timedelta(minutes=30):
            candidates.append((delta, -time.timestamp(), speed))
    if not candidates:
        return None, ''
    _, timestamp, speed = min(candidates)
    estimate = apparent_temperature(temp, humidity, speed * 1852 / 3600)
    observed_at = pd.Timestamp(-timestamp, unit='s', tz='UTC').tz_convert(now.tz)
    return estimate, f'Estimé · Vent de Charleroi à {observed_at:%H:%M}' if estimate is not None else ''


@st.cache_data(ttl=60, show_spinner=False)
def reves_reading():
    """Return the latest temperature and wind chill published by meteo-be.net."""
    try:
        response = requests.post(
            'https://meteo-be.net/api/graphql',
            json={'query': '{ station(slug: "reves") { recentData { temperature windchill date humidity wind_speed } } }'},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()['data']['station']['recentData']
        timestamp = pd.to_datetime(data['date'], utc=True, errors='coerce')
        temp = float(data['temperature']) - 273.15
        if pd.notna(timestamp) and isfinite(temp):
            try:
                feel, feel_source = station_feel(temp, data)
            except (TypeError, ValueError, OverflowError, ZeroDivisionError):
                feel, feel_source = None, ''
            return timestamp, temp, feel, feel_source, data.get('humidity')
    except (requests.RequestException, KeyError, TypeError, ValueError, OverflowError):
        pass
    return None


def distance_km(latitude, longitude, station_lat, station_lon):
    lat_delta = radians(station_lat - latitude)
    lon_delta = radians(station_lon - longitude)
    a = sin(lat_delta / 2) ** 2 + cos(radians(latitude)) * cos(radians(station_lat)) * sin(lon_delta / 2) ** 2
    return 12742 * asin(sqrt(min(1, a)))


@st.cache_data(ttl=60, show_spinner=False)
def network_readings():
    try:
        response = requests.post(
            'https://meteo-be.net/api/graphql',
            json={'query': '''{ stations { slug translations { fr { name } } locationCoords
                recentData { temperature windchill date humidity wind_speed } } }'''},
            timeout=6,
        )
        response.raise_for_status()
        stations = response.json()['data']['stations']
        return stations if isinstance(stations, list) else []
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return []


def closest_temperature(stations, reports, latitude, longitude, now):
    """Find the closest recent measured temperature within 15 km."""
    candidates = []

    def add(lat, lon, time, temp, label, feel, feel_source):
        if not all(isfinite(v) for v in (lat, lon, temp)) or not -80 <= temp <= 60:
            return
        if pd.isna(time) or not pd.Timedelta(minutes=-2) <= now - time <= pd.Timedelta(minutes=45):
            return
        distance = distance_km(latitude, longitude, lat, lon)
        if distance <= 15:
            candidates.append((distance, -time.timestamp(), time, temp, label, feel, feel_source))

    for station in stations:
        try:
            report = station['recentData']
            lat, lon = map(float, station['locationCoords'])
            time = pd.to_datetime(report['date'], utc=True, errors='coerce')
            temp = float(report['temperature']) - 273.15
            name = ((station.get('translations') or {}).get('fr') or {}).get('name') or station['slug']
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        try:
            feel, source = station_feel(temp, report)
        except (TypeError, ValueError, OverflowError):
            feel, source = None, ''
        add(lat, lon, time, temp, f'Station {name} · meteo-be.net', feel,
            'Calculé à partir des relevés de la station' if source else '')

    for report in reports:
        try:
            name = report['icaoId']
            lat, lon = float(report['lat']), float(report['lon'])
            time = pd.Timestamp(report['obsTime'], unit='s', tz='UTC')
            temp = float(report['temp'])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        feel = None
        try:
            dew = float(report['dewp'])
            wind = float(report['wspd'])
            if -80 <= dew <= temp <= 60 and 0 <= wind < 999:
                humidity = 100 * exp(17.27 * dew / (237.7 + dew) - 17.27 * temp / (237.7 + temp))
                feel = apparent_temperature(temp, humidity, wind * 1852 / 3600)
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
        add(lat, lon, time, temp, f'Station {name} · METAR', feel,
            'Calculé à partir du relevé METAR' if feel is not None else '')

    if not candidates:
        return None
    distance, _, time, temp, label, feel, feel_source = min(candidates, key=lambda entry: entry[:2])
    distance_text = f'{distance:.1f}'.replace('.', ',')
    return time, temp, feel, feel_source, f'{label} · {distance_text} km'
