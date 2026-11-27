"""Recherche de localités belges et correspondance avec les zones IRM."""

from dataclasses import dataclass
from unicodedata import normalize

import requests
import streamlit as st


@dataclass(frozen=True)
class Locality:
    name: str
    latitude: float
    longitude: float
    province: str
    irm_zone: str
    municipality: str = ''


DEFAULT_LOCALITY = Locality('Frasnes-lez-Gosselies', 50.532, 4.446, 'Hainaut', 'Hainaut')

PROVINCES = (
    ('Hainaut', ('hainaut', 'henegouwen')),
    ('Brabant (dont Bruxelles)', ('brabant', 'bruxelles', 'brussel', 'brussels')),
    ('Namur', ('namur', 'namen')),
    ('Liège', ('liege', 'luik')),
    ('Luxembourg', ('luxembourg', 'luxemburg')),
    ('Anvers', ('anvers', 'antwerp', 'antwerpen')),
    ('Limbourg', ('limbourg', 'limburg')),
    ('Flandre orientale', ('flandre orientale', 'oost-vlaanderen', 'east flanders')),
    ('Flandre occidentale', ('flandre occidentale', 'west-vlaanderen', 'west flanders')),
)


def region_for_irm(province):
    text = normalize('NFKD', province.casefold()).encode('ascii', 'ignore').decode()
    return next((zone for zone, names in PROVINCES if any(name in text for name in names)), '')


@st.cache_data(ttl=86400, show_spinner=False)
def search_localities(query):
    response = requests.get(
        'https://geocoding-api.open-meteo.com/v1/search',
        params={'name': query, 'countryCode': 'BE', 'language': 'fr', 'count': 20},
        timeout=10,
    )
    response.raise_for_status()
    localities = []
    for result in response.json().get('results', []):
        if result.get('country_code') != 'BE':
            continue
        province = result.get('admin2', '')
        localities.append(Locality(
            result['name'], float(result['latitude']), float(result['longitude']),
            province or result.get('admin1', ''),
            region_for_irm(province) or region_for_irm(result.get('admin1', '')),
            result.get('admin4', '') if result.get('admin4') != result['name'] else '',
        ))
    return list(dict.fromkeys(localities))
