"""Synthèse publique et graphiques des prévisions horaires."""
import base64
import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DAYS = ('Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim')


def ensemble(frames, index):
    data = pd.DataFrame(columns=["temp", "feel", "sun", "liquid", "rain", "wind", "gust", "code"], index=index, dtype=float)
    if frames:
        joined = pd.concat([frame.set_index('time') for frame in frames])
        numerical = joined.drop(columns=['code'])
        data = numerical.groupby(level=0).mean().reindex(index)
        # Les codes météo sont des catégories. Retenir le plus fréquent.
        codes = joined['code'].dropna()
        data['code'] = codes.groupby(level=0).agg(lambda values: values.mode().iloc[-1]).reindex(index)
        data['sources'] = joined['temp'].groupby(level=0).count().reindex(index, fill_value=0)
    return data


def weather(code, night=False):
    if pd.isna(code): return '…', 'Conditions indisponibles'
    if code == 0: return ('🌙' if night else '☀️'), 'Ciel dégagé'
    if code == 1: return ('🌙' if night else '🌤️'), 'Peu nuageux'
    if code == 2: return ('☁️' if night else '🌤️'), 'Partiellement nuageux'
    if code == 3: return '☁️', 'Couvert'
    if code <= 48: return '🌫️', 'Brouillard'
    if 71 <= code <= 77 or code in (85, 86): return '🌨️', 'Neige'
    if code >= 95: return '⛈️', 'Orage'
    return '🌧️', 'Précipitations'


def station_condition(row):
    """Applique les seuils du bandeau de Station Météo Final."""
    code = row.get('code', float('nan'))
    rain = row.get('rain', float('nan'))
    cloud = row.get('cloud', float('nan'))
    sun = row.get('sun', float('nan')) / 3600
    humidity, temp, dew, wind = (row.get(field, float('nan')) for field in ('rh', 'temp', 'dew', 'wind'))
    fog = code in (45, 48) or (humidity >= 95 and abs(temp - dew) <= 1.4 and wind <= 10)
    if fog:
        return 48 if code == 48 else 45, 'brouillard', 'Brouillard givrant' if code == 48 else 'Brume / brouillard possible'
    if code in (95, 96, 99):
        return code, 'orage', {95: 'Orage', 96: 'Orage avec grêle', 99: 'Orage violent'}[code]
    if code in (56, 57, 66, 67):
        return code, 'pluie_faible', 'Précipitations verglaçantes'
    if code in (71, 73, 75, 77, 85, 86):
        return code, None, weather(code)[1]
    if code in (51, 53, 55) and not rain >= 1:
        return code, 'bruine', {51: 'Bruine faible', 53: 'Bruine', 55: 'Bruine forte'}[code]
    if rain >= 4 or code in (65, 82):
        return 65, 'pluie_forte', 'Averses fortes' if code == 82 else 'Pluie forte'
    if rain >= 1 or code in (63, 81):
        icon = 'eclaircies_pluie' if sun >= .15 or cloud < 78 else 'pluie_moderee'
        return 63, icon, 'Averses' if code == 81 else 'Pluie'
    if rain > .05 or row.get('rain_probability', float('nan')) >= 45 or code in (51, 53, 55, 61, 80):
        icon = 'eclaircies_pluie' if sun >= .15 or cloud < 78 else 'pluie_faible'
        return 61, icon, 'Averses faibles' if code == 80 else 'Pluie faible'
    if code == 0 or cloud < 22:
        return 0, 'ciel_clair', 'Ciel clair'
    if sun >= .65 or code == 1 or cloud < 45:
        return 1, 'peu_nuageux', 'Peu nuageux'
    if sun >= .25 or code == 2 or cloud < 70:
        return 2, 'partiellement_nuageux', 'Partiellement nuageux'
    if code == 3 or pd.notna(cloud):
        return 3, 'tres_nuageux', 'Couvert'
    return code, None, weather(code)[1]


@st.cache_data(show_spinner=False)
def station_icon(asset):
    path = Path(__file__).parent / 'icons' / f'{asset}.png'
    return base64.b64encode(path.read_bytes()).decode('ascii')


def measure(value, unit, precision=0):
    return '—' if pd.isna(value) else f'{value:.{precision}f}{unit}'.replace('.', ',')


def hero(target, location, heading, row, conditions, observation, condition_hour):
    code, asset, condition = station_condition(conditions)
    night = conditions.get('daylight') == 0
    source = f'Estimation du ciel à {condition_hour:%H:%M}'
    if observation:
        observed_code, description, observation_source = observation
        source = observation_source if observed_code is not None else f'{source} · {observation_source.removeprefix("Conditions prévues · ")}'
        if observed_code is not None:
            code, asset, condition = station_condition({'code': observed_code})
            condition = description or condition
    if night and code == 0 and condition == 'Ciel clair':
        condition = 'Ciel serein'
    icon, _ = weather(code, night=night)
    if asset and not (night and asset in {'ciel_clair', 'peu_nuageux', 'partiellement_nuageux', 'eclaircies_pluie'}):
        try:
            icon = f'<img src="data:image/png;base64,{station_icon(asset)}" alt="" style="width:1.4em;height:1.4em;object-fit:contain">'
        except OSError:
            pass
    temp = measure(row.get('temp', float('nan')), ' °C', 1)
    feel = measure(row.get('feel', float('nan')), ' °C', 1)
    feel_source = row.get('feel_source', '')
    feel_note = f'<div class="sub">{html.escape(feel_source)}</div>' if feel_source else ''
    target.markdown(f'''<div class="hero"><h1>Météo</h1>
    <div class="sub">{html.escape(location)}</div>
    <div class="sub">© 2026 David Vergucht</div>
    <div class="sub">{html.escape(heading)} · Heure belge</div>
    <div class="forecast-current"><div><div class="forecast-temperature">{temp}</div>
    <div class="forecast-feel">Ressenti {feel}{feel_note}</div><div>{html.escape(condition)}</div></div><span aria-hidden="true">{icon}</span></div>
    <div class="sub">{html.escape(source)}</div></div>''', unsafe_allow_html=True)


def summary_icon(code, icon, label):
    asset = {1: 'peu_nuageux', 2: 'partiellement_nuageux'}.get(code)
    if asset:
        try:
            return (f'<img src="data:image/png;base64,{station_icon(asset)}" '
                    f'alt="{html.escape(label)}" title="{html.escape(label)}" '
                    'style="width:28px;height:28px;object-fit:contain;vertical-align:middle">')
        except OSError:
            pass
    return f'<span title="{html.escape(label)}">{icon}</span>'


def render_summary(week, days):
    st.caption('Min. / max. · Soleil estimé · Précipitations · Rafales max.')
    for day in days:
        hours = week.loc[week.index.date == day.date()]
        cells = [f'<strong>{DAYS[day.dayofweek]} <br>{day:%d/%m}</strong>']
        if hours.empty or hours['temp'].isna().all():
            cells.append('<span>Données indisponibles</span>')
        else:
            periods = [hours.between_time('06:00', '11:59'), hours.between_time('12:00', '17:59')]
            icons = []
            for period in periods:
                codes = period['code'].mode()
                code = codes.iloc[0] if not codes.empty else float('nan')
                icon, label = weather(code)
                icons.append(summary_icon(code, icon, label))
            cells += [
                ' → '.join(icons),
                f'{measure(hours.temp.min(), "°")} / {measure(hours.temp.max(), "°")}',
                f'<span class="mobile-metric">Soleil</span>☀️ {measure(hours.sun.sum(min_count=len(hours)) / 3600, " h", 1)}',
                f'<span class="mobile-metric">Pluie</span>💧 {measure(hours.rain.sum(min_count=len(hours)), " mm", 1)}',
                f'<span class="mobile-metric">Rafales</span>💨 {measure(hours.gust.max(), " km/h")}',
            ]
        st.markdown('<div class="forecast-day">' + ''.join(f'<div>{c}</div>' for c in cells) + '</div>',
                    unsafe_allow_html=True)


def render_charts(week, days):
    st.caption('Moyennes horaires · Heure belge')
    x = week.index.tz_localize(None)
    specs = [
        ('Température et ressenti', '°C', [('temp', 'Température', '#40c9ff'), ('feel', 'Ressenti', '#ffc55a')], False),
        ('Durée de soleil estimée', 'min/h', [('sun', 'Soleil', '#ffc55a')], True),
        ('Pluie prévue', 'mm/h', [('liquid', 'Pluie', '#40c9ff')], True),
        ('Vent et rafales', 'km/h', [('wind', 'Vent', '#70e0ed'), ('gust', 'Rafales', '#4c9dff')], False),
    ]
    for title, unit, traces, bars in specs:
        st.subheader(title)
        fig = go.Figure()
        for field, label, color in traces:
            values = week[field] / 60 if field == 'sun' else week[field]
            if not values.notna().any():
                continue
            if bars:
                fig.add_bar(x=x, y=values, name=label, marker_color=color)
            else:
                fig.add_scatter(x=x, y=values, name=label, line={'color': color}, mode='lines')
        if not fig.data:
            st.info('Aucune donnée disponible pour ce graphique.')
            continue
        fig.update_layout(
            template='plotly_dark', height=310, margin=dict(l=10, r=12, t=10, b=70),
            yaxis_title=unit, hovermode='x unified', legend=dict(orientation='h', y=-0.25),
        )
        fig.update_xaxes(tickvals=days.tz_localize(None),
                         ticktext=[f'{DAYS[d.dayofweek]}<br>{d:%d/%m}' for d in days],
                         hoverformat='%d/%m %H:%M')
        st.plotly_chart(fig, use_container_width=True, key=f'chart_{traces[0][0]}')
