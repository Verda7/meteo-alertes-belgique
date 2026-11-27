"""Avertissements officiels belges, relayés par MeteoAlarm."""

import re
from xml.etree import ElementTree as ET

import pandas as pd
import requests
import streamlit as st


FEED_URL = 'https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-belgium'
NS = {'atom': 'http://www.w3.org/2005/Atom', 'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
LEVELS = {'Minor': 0, 'Moderate': 1, 'Severe': 2, 'Extreme': 3}
COLORS = ('Vert', 'Jaune', 'Orange', 'Rouge')
COLOR_INDICATORS = {'Vert': '🟢', 'Jaune': '🟡', 'Orange': '🟠', 'Rouge': '🔴'}
# Libellés areaDesc du flux belge et libellés affichés dans l’application.
ZONES = {
    'Hainaut': 'Hainaut',
    'Brabant': 'Brabant (dont Bruxelles)',
    'Namur': 'Namur',
    'Liège': 'Liège',
    'Luxembourg': 'Luxembourg',
    'Antwerp': 'Anvers',
    'Limburg': 'Limbourg',
    'East Flanders': 'Flandre orientale',
    'West Flanders': 'Flandre occidentale',
    'Coastal zone': 'Zone côtière',
}
TYPES = {
    'ice snow': 'Neige et conditions glissantes', 'snow ice': 'Neige et conditions glissantes',
    'wind': 'Vent violent', 'rain': 'Fortes pluies', 'thunderstorm': 'Orages',
    'thunderstorms': 'Orages', 'fog': 'Brouillard', 'extreme high temperature': 'Fortes chaleurs',
    'extreme low temperature': 'Froid marqué', 'snow': 'Neige',
}


def parse_feed(content):
    root = ET.fromstring(content)
    if root.tag != f'{{{NS["atom"]}}}feed':
        raise ValueError('Format du flux officiel inattendu')
    warnings = {zone: [] for zone in ZONES.values()}
    for entry in root.findall('atom:entry', NS):
        def read(name):
            return (entry.findtext(f'cap:{name}', namespaces=NS) or '').strip()

        zone = ZONES.get(read('areaDesc'))
        if zone is None or read('status') != 'Actual' or read('scope') != 'Public':
            continue
        event = read('event')
        key = re.sub(r'^.*?warning for\s+', '', event.lower()).replace('-', ' ').strip()
        sent = pd.to_datetime(read('sent'), utc=True, errors='coerce')
        start = pd.to_datetime(read('onset') or read('effective') or read('sent'), utc=True, errors='coerce')
        end = pd.to_datetime(read('expires'), utc=True, errors='coerce')
        severity = LEVELS.get(read('severity'))
        if not key or severity is None or any(pd.isna(value) for value in (sent, start, end)):
            continue
        warnings[zone].append((sent, severity, start, end, read('message_type'), key, TYPES.get(key, event)))
    return warnings


@st.cache_data(ttl=600, show_spinner=False)
def official_feed():
    response = requests.get(FEED_URL, timeout=10)
    response.raise_for_status()
    return parse_feed(response.content)


def current_warnings(warnings, now, end, timezone):
    latest = sorted(warnings, key=lambda w: (w[0], -w[1]), reverse=True)
    selected = []
    for alert in latest:
        sent, severity, begin, expires, kind, key, title = alert
        if severity == 0 or kind == 'Cancel' or expires <= now or begin >= end or expires <= begin:
            continue

        def overlaps(other):
            return other[5] == key and other[2] < expires and other[3] > begin

        withdrawn = any(
            other[0] >= sent and (other[1] == 0 or other[4] == 'Cancel')
            and overlaps(other) and other[2] <= max(begin, now) and other[3] >= expires
            for other in latest
        )
        if not withdrawn and not any(overlaps(other) for other in selected):
            selected.append(alert)
    return [{
        'Avertissement': title,
        'Code': COLORS[severity],
        'Début': begin.tz_convert(timezone).strftime('%d/%m %H:%M'),
        'Fin': expires.tz_convert(timezone).strftime('%d/%m %H:%M'),
    } for _, severity, begin, expires, _, _, title in selected]
