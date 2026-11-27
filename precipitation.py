"""Types et cumuls des précipitations horaires."""

from math import isfinite

import pandas as pd


OPEN_METEO_TYPES = {
    51: 'Bruine faible', 53: 'Bruine modérée', 55: 'Bruine forte',
    56: 'Bruine verglaçante', 57: 'Bruine verglaçante',
    61: 'Pluie faible', 63: 'Pluie modérée', 65: 'Pluie forte',
    66: 'Pluie verglaçante', 67: 'Pluie verglaçante',
    71: 'Neige faible', 73: 'Neige modérée', 75: 'Neige forte', 77: 'Neige en grains',
    80: 'Averses faibles', 81: 'Averses modérées', 82: 'Averses fortes',
    85: 'Averses de neige', 86: 'Averses de neige fortes',
    96: 'Orage avec grêle', 99: 'Orage avec forte grêle',
}
METEOLOGIX_TYPES = {
    **OPEN_METEO_TYPES,
    50: 'Bruine faible', 52: 'Bruine modérée', 54: 'Bruine forte',
    58: 'Bruine et pluie', 59: 'Bruine et pluie',
    60: 'Pluie faible', 62: 'Pluie modérée', 64: 'Pluie forte',
    68: 'Pluie et neige', 69: 'Pluie et neige',
    70: 'Neige faible', 72: 'Neige modérée', 74: 'Neige forte',
    76: 'Cristaux de glace', 78: 'Cristaux de neige', 79: 'Granules de glace',
    83: 'Averse de pluie et neige', 84: 'Averse de pluie et neige',
    87: 'Neige roulée ou petite grêle', 88: 'Neige roulée ou petite grêle',
    89: 'Averse de grêle', 90: 'Averse de grêle',
}


def finite_number(value):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if isfinite(value) else None


def precipitation_label(row, source):
    total, rain, showers, snow = (
        finite_number(row.get(field)) for field in ('rain', 'liquid', 'showers', 'snow')
    )
    raw_code = finite_number(row.get('code'))
    code = int(raw_code) if raw_code is not None and raw_code.is_integer() else None
    has_total, has_rain, has_showers, has_snow = (
        value is not None and value > 0 for value in (total, rain, showers, snow)
    )
    types = METEOLOGIX_TYPES if source == 'Meteologix' else OPEN_METEO_TYPES
    wet = has_total or has_rain or has_showers or has_snow
    if code in (56, 57, 66, 67, 96, 99):
        label = types[code]
    elif has_snow and (has_rain or has_showers):
        label = 'Pluie et neige'
    elif code in (95, 97) and wet:
        label = 'Précipitations orageuses'
    elif code in types:
        label = types[code]
    elif has_snow:
        label = 'Neige'
    elif has_showers:
        label = 'Averses'
    elif has_rain:
        label = 'Pluie'
    elif wet:
        label = 'Type indéterminé'
    else:
        return 'Sec' if total == 0 or code in (0, 1, 2, 3, 45, 48) else 'Donnée indisponible'

    amounts = [f'{total:.2f} mm'.replace('.', ',')] if has_total else []
    if has_snow:
        amounts.append(f'{snow:.2f} cm de neige'.replace('.', ','))
    return ' · '.join([label, *amounts])


def precipitation_table(datasets, interval_starts):
    table = pd.DataFrame(index=interval_starts)
    interval_ends = interval_starts + pd.Timedelta(hours=1)
    for name, values in datasets.items():
        rows = values.set_index('time').reindex(interval_ends)
        table[name] = [precipitation_label(row, name) for _, row in rows.iterrows()]
    return table
