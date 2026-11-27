"""Observations METAR récentes à proximité de la localité choisie."""

from math import asin, cos, radians, sin, sqrt
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
        lat_delta = radians(lat - latitude)
        lon_delta = radians(lon - longitude)
        a = sin(lat_delta / 2) ** 2 + cos(radians(latitude)) * cos(radians(lat)) * sin(lon_delta / 2) ** 2
        distance = 12742 * asin(sqrt(min(1, a)))
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
