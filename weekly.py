"""Synthèse publique et graphiques des prévisions horaires."""
import html

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


def weather(code):
    if pd.isna(code): return '…', 'Conditions indisponibles'
    if code == 0: return '☀️', 'Ciel dégagé'
    if code <= 2: return '🌤️', 'Partiellement nuageux'
    if code == 3: return '☁️', 'Couvert'
    if code <= 48: return '🌫️', 'Brouillard'
    if 71 <= code <= 77 or code in (85, 86): return '🌨️', 'Neige'
    if code >= 95: return '⛈️', 'Orage'
    return '🌧️', 'Précipitations'


def measure(value, unit, precision=0):
    return '—' if pd.isna(value) else f'{value:.{precision}f}{unit}'.replace('.', ',')


def hero(target, location, hour, row):
    icon, condition = weather(row.get('code', float('nan')))
    temp = measure(row.get('temp', float('nan')), ' °C', 1)
    feel = measure(row.get('feel', float('nan')), ' °C', 1)
    count = int(row.get('sources', 0))
    target.markdown(f'''<div class="hero"><h1>Météo</h1>
    <div class="sub">{html.escape(location)}</div>
    <div class="sub">© 2026 David Vergucht</div>
    <div class="sub">Prochaine heure · {hour:%d/%m %H:%M} · Heure belge</div>
    <div class="forecast-current"><div><div class="forecast-temperature">{temp}</div>
    <div>Ressenti {feel}</div><div>{condition}</div></div><span aria-hidden="true">{icon}</span></div>
    <div class="sub">{count} modèle(s) pour la température</div></div>''', unsafe_allow_html=True)


def render_summary(week, days):
    st.caption('Min. / max. · Soleil estimé · Précipitations · Rafales max.')
    for day in days:
        hours = week.loc[week.index.date == day.date()]
        cells = [f'<strong>{DAYS[day.dayofweek]}<br>{day:%d/%m}</strong>']
        if hours.empty or hours['temp'].isna().all():
            cells.append('<span>Données indisponibles</span>')
        else:
            periods = [hours.between_time('06:00', '11:59'), hours.between_time('12:00', '17:59')]
            icons = []
            for period in periods:
                codes = period['code'].mode()
                icon, label = weather(codes.iloc[0] if not codes.empty else float('nan'))
                icons.append(f'<span title="{label}">{icon}</span>')
            cells += [
                ' → '.join(icons),
                f'{measure(hours.temp.min(), "°")} / {measure(hours.temp.max(), "°")}',
                f'☀️ {measure(hours.sun.sum(min_count=len(hours)) / 3600, " h", 1)}',
                f'💧 {measure(hours.rain.sum(min_count=len(hours)), " mm", 1)}',
                f'💨 {measure(hours.gust.max(), " km/h")}',
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
