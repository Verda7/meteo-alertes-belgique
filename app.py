"""Météo Alertes — Belgique. © 2026 David Vergucht.
Application Streamlit de surveillance météorologique locale.
"""
from __future__ import annotations
import html
import math
from datetime import timezone
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import streamlit as st
from streamlit.components.v1 import iframe
from streamlit_searchbox import st_searchbox
from weekly import ensemble, hero as render_forecast_hero, render_summary, render_charts
from localities import DEFAULT_LOCALITY, search_localities
from observations import (belgian_reports, charleroi_feel, closest_temperature,
                          nearby_observation, network_readings, reves_reading)
from official import COLORS as IRM_COLORS, COLOR_INDICATORS, ZONES, current_warnings, official_feed
from xml.etree.ElementTree import ParseError

BELGIAN_TIME = ZoneInfo('Europe/Brussels')
ICE_RISK_LABEL = 'Givre / Plaques de glace / Verglas'
FROST_LEVELS = ('Aucun risque', 'Faible', 'Modéré', 'Fort', 'Sévère')
PUBLIC_RISKS = {
    'verglas': 'Le risque de givre ou de plaques de glace est également présent.',
    'brouillard': 'De la brume ou du brouillard pourrait localement réduire la visibilité.',
    'neige': 'Des chutes de neige sont à prévoir par endroits.',
    'vent': 'De fortes rafales de vent sont à prévoir.',
    'pluie': 'De fortes précipitations sont à prévoir.',
    'orage': 'Des orages pourraient se développer localement.',
}

TZ = BELGIAN_TIME
MODELS = {
    'AROME HD': ('forecast', 'meteofrance_arome_france_hd'),
    'ICON-D2': ('forecast', 'dwd_icon_d2_native'),
    'ECMWF IFS': ('forecast', 'ecmwf_ifs025'),
    'ICON-EU': ('forecast', 'dwd_icon_eu_native'),
    'ICON Global': ('forecast', 'icon_global'),
}
CONDITION_MODELS = ('AROME HD', 'ICON-D2')
OPENING_MODELS = ('AROME HD', 'ICON-D2', 'ECMWF IFS', 'ICON Global')
WEEKLY_MODELS = ('AROME HD', 'ICON-D2', 'ICON-EU', 'ECMWF IFS')
RADAR_URL = 'https://www.meteo.be/fr/meteo/previsions/precipitations'
PARAMS = {
    'temperature_2m':'temp', 'apparent_temperature':'feel', 'sunshine_duration':'sun', 'relative_humidity_2m':'rh',
    'dew_point_2m':'dew', 'precipitation':'rain', 'snowfall':'snow',
    'precipitation_probability':'rain_probability', 'wind_speed_10m':'wind', 'wind_gusts_10m':'gust',
    'is_day':'daylight', 'cloud_cover_low':'lowcloud', 'cloud_cover':'cloud',
    'visibility':'visibility', 'weather_code':'code',
    'soil_temperature_0cm':'ground', 'rain':'liquid', 'showers':'showers', 'cape':'cape',
}
EVENTS = [
    ('gel','❄️','Gel de l’air'),('gel_sol','❄️','Gel au sol'),
    ('verglas','🧊',ICE_RISK_LABEL),
    ('neige','🌨️','Neige'),('vent','💨','Vent violent'),
    ('pluie','🌧️','Fortes pluies'),('orage','⛈️','Orages'),
    ('brouillard','🌫️','Brouillard'),
]
LEVELS = ('Aucun risque', 'Faible', 'Modéré', 'Élevé', 'Très élevé')
FROST_KEYS = {'gel', 'gel_sol'}
FROST_CRITERIA = 'Faible dès 0 °C, modéré dès −5 °C, fort dès −10 °C et sévère dès −15 °C.'
CSS = '''
<style>
.block-container{max-width:1160px;padding-bottom:2rem}
[data-testid="stMainBlockContainer"], .block-container{padding-top:3.5rem!important}
#MainMenu,footer{visibility:hidden}
.hero{background:linear-gradient(155deg,#0856d6,#0b398c 62%,#102349);color:white;border-radius:22px;padding:22px 24px;margin:0 0 18px;box-shadow:0 10px 30px #09182720}
.hero .eyebrow{font-size:12px;letter-spacing:2px;color:#a8d8ec;font-weight:800}
.hero h1{font-size:clamp(23px,4vw,34px);line-height:1.16;margin:7px 0;color:#fff!important}
.hero .sub{color:#e6efff;font-size:15px;margin:4px 0}
.forecast-current{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:16px 0}
.forecast-current > span{font-size:clamp(34px,8vw,64px)}
.forecast-feel{font-size:clamp(20px,4vw,30px);margin:4px 0 10px}
.forecast-temperature{font-size:clamp(38px,10vw,66px);line-height:1.15;font-weight:800}
.forecast-day{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));align-items:center;
    background:linear-gradient(115deg,#153b78,#12274b);color:white;border:1px solid #648cc189;
    border-radius:16px;padding:12px;margin-bottom:6px;text-align:center;font-size:14px;gap:8px}
.forecast-day > div:not(:first-child){border-left:1px solid #aac8ef55;padding-left:6px}
@media(max-width:520px){.forecast-day{grid-template-columns:repeat(3,minmax(0,1fr));font-size:13px}}
.risk{background:rgba(120,145,165,.07);border:1px solid rgba(135,153,176,.22);border-radius:17px;padding:16px 17px;margin:0 0 11px}
.risk .top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.risk .name{font-weight:800;font-size:17px}
.risk .desc{font-size:13px;opacity:.82;margin-top:9px;line-height:1.5}
.risk .times{font-size:12px;opacity:.84;margin-top:9px}
.pill{display:inline-block;border-radius:100px;padding:5px 11px;font-weight:800;font-size:11px;white-space:nowrap}
.pill-none{background:#2f9c7830;color:#46b994}.pill-low{background:#62a7e52b;color:#62a7e5}
.pill-mid{background:#d6a22d30;color:#d9a53b}.pill-high{background:#e16a3630;color:#f38a58}
.pill-extreme{background:#d44e6430;color:#f47d91}
.mini{border:1px solid rgba(135,153,176,.25);border-radius:15px;padding:15px 14px;background:rgba(125,144,166,.06);min-height:108px}
.mini .label{font-size:12px;opacity:.72}.mini .value{font-size:clamp(21px,4vw,28px);font-weight:850;margin:7px 0 3px}.mini .hint{font-size:11px;opacity:.65}
.section{font-weight:800;font-size:19px;margin:19px 0 12px}
.note{font-size:12px;opacity:.75;line-height:1.6}
@media(max-width:650px), (max-width:950px) and (pointer:coarse){
    .block-container{padding-left:12px!important;padding-right:12px!important}
    .hero{padding:19px 17px;border-radius:18px}
    .hero .eyebrow{line-height:1.4}
    .risk{padding:13px}.risk .name{font-size:15px}.mini{padding:12px;min-height:99px}
}

.st-key-bulletin_card {
    container-type: inline-size;
    padding: 16px;
    background: linear-gradient(155deg, #fff0d5 0%, #f6e2bf 45%, #ead1a7 100%);
    border: 1px solid #d5ae70;
    border-radius: 22px;
    box-shadow: 0 10px 26px #3a291a38;
    overflow: hidden;
}
.st-key-bulletin_card .bulletin-title {
    color: #000;
    text-align: center;
    font-weight: 800;
    font-size: clamp(10px, 4.3vw, 24px);
    font-size: min(5cqi, 24px);
    white-space: nowrap;
    line-height: 1.3;
}
/* Clear the Streamlit editor wrappers as well as the native input. */
.st-key-bulletin_card .bulletin-body {
    color: #000;
    text-align: left;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: 16px;
    line-height: 1.58;
}
</style>
'''
st.set_page_config(page_title='Météo Alertes | Belgique',page_icon='⚠️',layout='wide')
st.markdown(CSS,unsafe_allow_html=True)


def make_public_bulletin(alerts, start, end, locality_label):
    levels = {
        key: max(
            (event['level'] for event in events
             if event['start'] < end and event['end'] > start),
            default=0,
        )
        for key, events in alerts.items()
    }
    air, ground = levels.get('gel', 0), levels.get('gel_sol', 0)
    sentences = []
    if air and air == ground:
        sentences.append(f'un risque de gel {FROST_LEVELS[air].lower()} dans l’air et au sol.')
    elif air or ground:
        frost = [
            f'un risque de gel {FROST_LEVELS[level].lower()} {label}'
            for level, label in ((air, 'dans l’air'), (ground, 'au sol'))
            if level
        ]
        sentences.append(' et '.join(frost) + '.')

    for key, sentence in PUBLIC_RISKS.items():
        if levels.get(key, 0):
            sentences.append(sentence.replace(' également', '') if not sentences else sentence)
    if not sentences:
        return None

    hours = round((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() / 3600)
    intro = f'Sur les prochaines {hours} heures, '
    if air or ground:
        intro += 'les modèles indiquent '
    else:
        sentences[0] = sentences[0][0].lower() + sentences[0][1:]

    precaution = 'La prudence est de mise lors des déplacements'
    if levels.get('verglas') and levels.get('brouillard'):
        precaution += ', en particulier là où la visibilité diminue et où la chaussée est humide'
    elif levels.get('brouillard'):
        precaution += ', en particulier là où la visibilité diminue'
    elif levels.get('verglas'):
        precaution += ', en particulier là où la chaussée est humide'

    return '\n'.join([
        '⚠️ BULLETIN D’AVERTISSEMENTS ⚠️',
        f'📍 {locality_label}',
        '',
        intro + ' '.join(sentences),
        '',
        precaution + '.',
    ])


def number(x):
    if isinstance(x,dict):x=x.get('value')
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):return None


@st.cache_data(ttl=600,show_spinner=False)
def open_model(endpoint, model, latitude, longitude):
    url=f'https://api.open-meteo.com/v1/{endpoint}'
    base={'latitude':latitude,'longitude':longitude,'timezone':'Europe/Brussels','timeformat':'unixtime','forecast_days':7,
          'models':model,'wind_speed_unit':'kmh','temperature_unit':'celsius','precipitation_unit':'mm'}
    # Reduce fields progressively: not every model supports every variable.
    groups=[list(PARAMS),[x for x in PARAMS if x not in ('visibility','dew_point_2m','cloud_cover_low')],
            ['temperature_2m','apparent_temperature','sunshine_duration','is_day','relative_humidity_2m','precipitation','rain','snowfall','wind_speed_10m','wind_gusts_10m','weather_code','cloud_cover'],
            ['temperature_2m','precipitation','wind_gusts_10m']]
    reasons=[]
    for group in groups:
        try:
            response=requests.get(url,params={**base,'hourly':','.join(group)},timeout=10)
            data=response.json()
            if response.status_code!=200 or data.get('error'):
                reasons.append(str(data.get('reason',f'HTTP {response.status_code}'))[:130]);continue
            hourly=data.get('hourly') or {}
            dates=hourly.get('time') or []
            if not dates:reasons.append('Aucune prévision horaire');continue
            timestamps = pd.to_datetime(dates, unit='s', utc=True, errors='coerce').tz_convert(TZ)
            df=pd.DataFrame({'time':timestamps})
            for api,field in PARAMS.items():
                values=hourly.get(api)
                df[field]=pd.to_numeric(pd.Series(values),errors='coerce') if isinstance(values,list) and len(values)==len(dates) else float('nan')
            return df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
        except (requests.RequestException,ValueError,TypeError) as exc:reasons.append(str(exc)[:130])
    raise ValueError(' / '.join(dict.fromkeys(reasons))[:260])


def subset(df,start,end):
    return df.loc[(df.time>=start)&(df.time<end)].copy().reset_index(drop=True)


def series(df,key):
    if key not in df:return pd.Series(dtype=float)
    return pd.to_numeric(df[key],errors='coerce').dropna()


def aggregate(datasets, key, op, hours):
    """Calcule une valeur par modèle, en ignorant les données manquantes."""
    vals = []
    for name, df in datasets.items():
        s = series(df, key)
        if s.empty:
            continue
        if op == 'min':
            value = s.min()
        elif op == 'max':
            value = s.max()
        elif op == 'sum':
            if len(s) != hours:
                continue
            value = s.clip(lower=0).sum()
        else:
            raise ValueError(f'Opération non reconnue : {op}')
        value = number(value)
        if value is not None:
            vals.append((name, value))
    return vals


def choose_aggregate(datasets, key, op, method, hours):
    vals = aggregate(datasets, key, op, hours)
    if not vals:
        return None, 0
    values = [value for _, value in vals]
    if method == 'Prudente':
        result = min(values) if op == 'min' else max(values)
    else:
        result = sum(values) / len(values)
    return float(result), len(values)


def event_from_frame(df):
    """Hourly heuristic levels. No claims of observed ice/visibility when unmeasured."""
    x=df.copy()
    for col in PARAMS.values():
        if col not in x:x[col]=float('nan')
    temp=pd.to_numeric(x.temp,errors='coerce')
    rain=pd.to_numeric(x.rain,errors='coerce')
    snow=pd.to_numeric(x.snow,errors='coerce')
    gust=pd.to_numeric(x.gust,errors='coerce')
    rh=pd.to_numeric(x.rh,errors='coerce')
    dew=pd.to_numeric(x.dew,errors='coerce')
    vis=pd.to_numeric(x.visibility,errors='coerce')
    lowcloud=pd.to_numeric(x.lowcloud,errors='coerce')
    codes=pd.to_numeric(x.code,errors='coerce')
    result={k:pd.Series(0,index=x.index,dtype=int) for k,_,_ in EVENTS}
    for key, temperatures in [('gel', temp), ('gel_sol', pd.to_numeric(x.ground, errors='coerce'))]:
        result[key] = pd.Series(0, index=x.index, dtype=int)
        for level, threshold in enumerate((0, -5, -10, -15), start=1):
            result[key] = result[key].mask(temperatures <= threshold, level)
    # Proxy: low air temp + moisture/precipitation; not a measurement of road ice.
    wet=(rain.fillna(0)>0.05) | (rh>=92)
    result['verglas']=pd.Series(0,index=x.index,dtype=int).mask((temp<=1)&wet,1).mask((temp<=0)&wet,2).mask((temp<=-2)&(rain.fillna(0)>0.05),3).mask(codes.isin([56,57,66,67]),3)
    result['neige']=pd.Series(0,index=x.index,dtype=int).mask(snow>0,1).mask(snow>=0.5,2).mask(snow>=2,3).mask(snow>=5,4)
    result['vent']=pd.Series(0,index=x.index,dtype=int).mask(gust>=60,1).mask(gust>=75,2).mask(gust>=90,3).mask(gust>=110,4)
    result['pluie']=pd.Series(0,index=x.index,dtype=int).mask(rain>=2,1).mask(rain>=5,2).mask(rain>=10,3).mask(rain>=20,4)
    result['orage']=pd.Series(0,index=x.index,dtype=int).mask(codes.isin([95,96,97,99]),2).mask(codes.isin([96,97,99]),3)
    # True visibility preferred; humidity/low cloud proxy only indicates *potential*.
    fog=pd.Series(0,index=x.index,dtype=int).mask(vis<1000,1).mask(vis<500,2).mask(vis<200,3).mask(vis<50,4)
    proxy=(rh>=97)&((temp-dew)<=1.0)&(lowcloud>=70)
    fog=fog.mask(vis.isna()&proxy,1)
    result['brouillard']=fog
    return result


def segments(df,level_series):
    active=[]
    for i,v in enumerate(level_series):
        if int(v)>0:active.append(i)
    if not active:return []
    groups=[[active[0]]]
    for i in active[1:]:
        dt=(df.time.iloc[i]-df.time.iloc[groups[-1][-1]]).total_seconds()
        if i==groups[-1][-1]+1 and dt<=5400:groups[-1].append(i)
        else:groups.append([i])
    out=[]
    for g in groups:
        peak=max(int(level_series.iloc[i]) for i in g)
        best=next(i for i in g if int(level_series.iloc[i])==peak)
        out.append({'start':df.time.iloc[g[0]],'end':df.time.iloc[g[-1]]+pd.Timedelta(hours=1),
                    'peak_time':df.time.iloc[best],'level':peak})
    return out


def analyze(datasets):
    events={k:[] for k,_,_ in EVENTS}
    for model,df in datasets.items():
        lv=event_from_frame(df)
        for key,_,_ in EVENTS:
            for item in segments(df,lv[key]):events[key].append({'model':model,**item})
    return events


def level_name(key, level):
    return (FROST_LEVELS if key in FROST_KEYS else LEVELS)[level]


def badge(key, level):
    label = level_name(key, level)
    klass=['none','low','mid','high','extreme'][level]
    return f'<span class="pill pill-{klass}">{label}</span>'


def short_time(t):return pd.Timestamp(t).strftime('%d/%m %Hh')


def card(key,emoji,title,items,available):
    if not items:
        label='Données insuffisantes' if not available else 'Aucun signal détecté'
        st.markdown(f'<div class="risk"><div class="top"><span class="name">{emoji} {title}</span>{badge(key, 0)}</div><div class="desc">{label} sur la période sélectionnée.</div></div>',unsafe_allow_html=True)
        return
    peak=max(items,key=lambda v:v['level'])
    start=min(i['start'] for i in items);end=max(i['end'] for i in items)
    names=sorted(set(i['model'] for i in items))
    desc={'gel':'Température de l’air à 2 m. ' + FROST_CRITERIA,
          'gel_sol':'Température de surface du sol. ' + FROST_CRITERIA,
          'verglas':'Risque indicatif de surfaces glissantes ; pas une prévision directe de température de chaussée.',
          'neige':'Chutes de neige prévues par au moins un modèle.',
          'vent':'Rafales pouvant devenir dangereuses.',
          'pluie':'Précipitations horaires potentiellement intenses.',
          'orage':'Signal orageux basé sur les codes météo disponibles ; pas une analyse CAPE/CIN.',
          'brouillard':'Visibilité prévue si disponible ; sinon signal indicatif basé sur humidité, point de rosée et nuages bas.'}[key]
    st.markdown(f'''<div class="risk"><div class="top"><span class="name">{emoji} {title}</span>{badge(key, peak['level'])}</div>
    <div class="times">🕒 Début : <b>{short_time(start)}</b> &nbsp;·&nbsp; Pic : <b>{short_time(peak['peak_time'])}</b> &nbsp;·&nbsp; Fin : <b>{short_time(end)}</b></div>
    <div class="desc">{html.escape(desc)}<br>Modèles signalant le risque : {html.escape(', '.join(names))}.</div></div>''',unsafe_allow_html=True)


def mini(label,value,hint):
    st.markdown(f'<div class="mini"><div class="label">{html.escape(label)}</div><div class="value">{html.escape(value)}</div><div class="hint">{html.escape(hint)}</div></div>',unsafe_allow_html=True)


def locality_suggestions(query):
    query = query.strip()
    if len(query) < 2 or len(query) > 100:
        return []
    try:
        return [
            (' · '.join(filter(None, (place.name, place.municipality, place.province))), place)
            for place in search_localities(query)
        ]
    except (requests.RequestException, ValueError, KeyError, TypeError):
        st.warning('Recherche de localités temporairement indisponible.')
        return []


hero = st.container()
locality = st_searchbox(
    locality_suggestions, label='Localité en Belgique',
    placeholder='Ex. Namur ou 5000', debounce=350, edit_after_submit='option',
    default_options=[('Frasnes-lez-Gosselies · Hainaut', DEFAULT_LOCALITY)],
    key='locality_autocomplete',
) or DEFAULT_LOCALITY
latitude, longitude = locality.latitude, locality.longitude
horizon = st.segmented_control('Période de vigilance et du bulletin', ['24 heures', '48 heures'],
                               default='24 heures', key='horizon')

now = pd.Timestamp.now(tz=TZ)
start = now.tz_convert('UTC').floor('h').tz_convert(TZ)
hours = 24 if horizon == '24 heures' else 48
end = start + pd.Timedelta(hours=hours)
all_datasets = {}
errors = {}
with st.spinner('Analyse des prévisions en cours…'):
    for name, (endpoint, model) in MODELS.items():
        try:
            frame = open_model(endpoint, model, latitude, longitude)
            if frame['temp'].notna().any():
                all_datasets[name] = frame
            else:
                errors[name] = 'Aucune donnée à cet endroit.'
        except (ValueError, requests.RequestException, TypeError) as exc:
            errors[name] = str(exc)[:220]

@st.fragment(run_every=60)
def live_hero():
    current_time = pd.Timestamp.now(tz=TZ)
    current_hour = current_time.tz_convert('UTC').floor('h').tz_convert(TZ)
    hour_index = pd.DatetimeIndex([current_hour])
    conditions = ensemble([all_datasets[name] for name in CONDITION_MODELS if name in all_datasets],
                          hour_index).iloc[0]
    reports = belgian_reports()
    observation = nearby_observation(reports, latitude, longitude, current_time)
    is_reves_area = locality.name.casefold() in {'rèves', 'frasnes-lez-gosselies', 'les bons villers'}
    reading = reves_reading() if is_reves_area else None
    measured = None
    if reading and pd.Timedelta(minutes=-2) <= current_time - reading[0] <= pd.Timedelta(minutes=30):
        measured_at, temp, feel, feel_source, humidity = reading
        if feel is None:
            feel, feel_source = charleroi_feel(reports, temp, humidity, measured_at, current_time)
        measured = measured_at, temp, feel, feel_source, 'Station météo de Rèves'
    if not measured:
        measured = closest_temperature(network_readings(), reports, latitude, longitude, current_time)

    if measured:
        measured_at, temp, feel, feel_source, station = measured
        heading = f'{station} · Relevé du {measured_at.tz_convert(TZ):%d/%m à %H:%M}'
        if feel is None:
            estimated = ensemble([all_datasets[name] for name in OPENING_MODELS if name in all_datasets],
                                 hour_index).iloc[0]
            feel = estimated.get('feel', float('nan'))
            if pd.notna(feel):
                feel_source = 'Estimation locale des modèles'
        values = {'temp': temp, 'feel': feel, 'feel_source': feel_source}
    else:
        heading = f'Estimation locale · {current_hour:%d/%m à %H:%M}'
        values = ensemble([all_datasets[name] for name in OPENING_MODELS if name in all_datasets],
                          hour_index).iloc[0]
    render_forecast_hero(st, locality.name, heading, values, conditions, observation, current_hour)


with hero:
    live_hero()

first_day = now.normalize()
days = pd.date_range(first_day, periods=7, freq='D')
week_index = pd.date_range(first_day, first_day + pd.DateOffset(days=7), freq='h', inclusive='left')
week = ensemble([all_datasets[name] for name in WEEKLY_MODELS if name in all_datasets], week_index)
datasets = {}
for name in WEEKLY_MODELS:
    if name not in all_datasets:
        continue
    frame = all_datasets[name]
    window = subset(frame, start, end)
    if window['temp'].notna().any():
        datasets[name] = window
mode = 'Prudente'
alerts=analyze(datasets)
peaks = {key: max((item['level'] for item in alerts[key]), default=0) for key, _, _ in EVENTS}
max_level = max(peaks.values(), default=0)
st.markdown(f'**{len(datasets)} source(s) active(s)** · Mis à jour à {now.strftime("%H:%M")} · Analyse sur {24 if horizon=="24 heures" else 48} h')
if max_level:
    risks = ' · '.join(
        f'{label} ({level_name(key, peaks[key]).lower()})'
        for key, _, label in sorted(EVENTS, key=lambda event: -peaks[event[0]]) if peaks[key]
    )
    banner = st.error if max_level >= 3 else st.warning
    banner(f'⚠️ **Risques à surveiller** : {risks}')
elif datasets:st.success('✅ Aucun signal de danger détecté dans les paramètres actuellement disponibles.')

summary_tab, graphs_tab, radar_tab, public_tab, vigilance_tab, irm_tab = st.tabs(
    ['Résumé 7 jours', 'Graphiques 7 jours', 'Radar pluie', 'Bulletin',
     'Vigilance locale', 'Alertes IRM']
)

with summary_tab:
    render_summary(week, days)

with graphs_tab:
    render_charts(week, days)

with radar_tab:
    st.link_button('Ouvrir le radar de l’IRM', RADAR_URL)
    iframe(RADAR_URL, height=600, scrolling=True)

with vigilance_tab:
    st.markdown('<div class="section">Vue d’ensemble</div>',unsafe_allow_html=True)
    min_temp,n_temp=choose_aggregate(datasets,'temp','min',mode,hours)
    gust,n_gust=choose_aggregate(datasets,'gust','max',mode,hours)
    rain,n_rain=choose_aggregate(datasets,'rain','sum',mode,hours)
    max_snow,n_snow=choose_aggregate(datasets,'snow','sum',mode,hours)
    c1,c2=st.columns(2)
    with c1:mini('🌡️ Minimum (modèles actifs)',f'{min_temp:.1f} °C' if min_temp is not None else '—',f'{n_temp} modèle(s) · {mode.lower()}')
    with c2:mini('💨 Rafales maximales',f'{gust:.0f} km/h' if gust is not None else '—',f'{n_gust} modèle(s)')
    c3,c4=st.columns(2)
    with c3:mini('🌧️ Cumul de précipitations',f'{rain:.1f} mm' if rain is not None else '—',f'{n_rain} modèle(s)')
    with c4:mini('🌨️ Cumul neige (indicatif)',f'{max_snow:.1f} cm' if max_snow is not None else '—',f'{n_snow} modèle(s)')
    st.caption('Les cumuls utilisent les modèles qui disposent de toutes les échéances de la période.')

    st.markdown('<div class="section">Avertissements prioritaires</div>',unsafe_allow_html=True)
    ordered=sorted(EVENTS,key=lambda item:max((i['level'] for i in alerts[item[0]]),default=0),reverse=True)
    for key,emoji,title in ordered:
        available={'gel':'temp','gel_sol':'ground','verglas':'temp','neige':'snow','vent':'gust','pluie':'rain','orage':'code','brouillard':'visibility'}[key]
        has_data=any(not series(df,available).empty for df in datasets.values())
        if key=='brouillard':
            has_data=has_data or any(all(not series(df,c).empty for c in ('rh','dew','lowcloud')) for df in datasets.values())
        card(key,emoji,title,alerts[key],has_data)

with irm_tab:
    st.markdown('[Consulter les avertissements officiels de l’IRM](https://www.meteo.be/fr/meteo/avertissements)')
    st.caption(f'Source · IRM via MeteoAlarm · niveau maximal sur la période sélectionnée ({hours} h)')
    try:
        feed = official_feed()
        warnings_by_zone = {zone: current_warnings(entries, now, end, TZ) for zone, entries in feed.items()}
    except (requests.RequestException, ParseError, ValueError):
        warnings_by_zone = None
        st.warning('Le flux officiel est temporairement indisponible. Consulte le site de l’IRM.')
    overview = []
    for zone in ZONES.values():
        if warnings_by_zone is None:
            indicator = '⚪ Indisponible'
        else:
            color = max((warning['Code'] for warning in warnings_by_zone[zone]),
                        key=IRM_COLORS.index, default='Vert')
            indicator = f'{COLOR_INDICATORS[color]} {color}'
        overview.append({'Zone': zone, 'Vigilance': indicator})
    st.dataframe(pd.DataFrame(overview), hide_index=True, use_container_width=True, height=390)
    zones = list(ZONES.values())
    if st.session_state.get('irm_locality') != locality:
        st.session_state.irm_locality = locality
        st.session_state.irm_zone = locality.irm_zone or None
    zone = st.selectbox('Zone à consulter', zones, index=None, key='irm_zone')
    if warnings_by_zone is not None and zone is not None:
        warnings = warnings_by_zone[zone]
        if warnings:
            details = pd.DataFrame(warnings)
            details['Code'] = details['Code'].map(lambda color: f'{COLOR_INDICATORS[color]} {color}')
            st.dataframe(details, hide_index=True, use_container_width=True)
        else:
            st.info(f'{zone} · Aucun avertissement signalé sur la période.')

with public_tab:
    st.subheader('Bulletin d’avertissements')
    if locality.irm_zone:
        st.caption(f'Zone IRM de la localité · {locality.irm_zone}')
    st.caption('Vigilance locale calculée à partir des modèles.')
    public_text = make_public_bulletin(alerts, start, end, locality.name)
    if not any(not frame.empty for frame in datasets.values()):
        st.info('Données insuffisantes pour préparer le bulletin.')
    elif public_text is None:
        st.info('Aucun risque détecté sur la période avec les données disponibles.')
    else:
        title, body = public_text.split('\n', 1)
        with st.container(key='bulletin_card'):
            st.markdown(
                f'<div class="bulletin-title">{html.escape(title)}</div>'
                f'<div class="bulletin-body">{html.escape(body)}</div>',
                unsafe_allow_html=True,
            )
        st.download_button('Télécharger le bulletin public (.txt)', data=public_text,
                           file_name='bulletin_avertissements.txt', mime='text/plain')


with st.expander('🔎 Diagnostic des données et limites',expanded=False):
    for name,df in all_datasets.items():
        fields=', '.join(k for k in ('temp','rain','snow','gust','rh','dew','visibility','lowcloud','code') if not series(df,k).empty)
        st.write(f'**{name}** : {len(df)} échéances · {fields or "aucun paramètre"}')
    for name,error in errors.items():st.warning(f'{name} : {error}')
    st.caption('Verglas : estimation à partir de la température de l’air et de l’humidité/pluie, pas une observation de la chaussée. Brouillard : estimation si visibilité absente. Orages : codes météo, pas diagnostic convectif complet.')

st.markdown('<div class="note" style="text-align:center;margin-top:30px;padding-top:17px;border-top:1px solid #8b9aad33">Données : Open-Meteo (AROME HD, ICON-D2, ECMWF IFS, ICON-EU et ICON Global selon disponibilité.<br>© 2026 David Vergucht — Tous droits réservés.<br>Outil indicatif : ne remplace pas les avertissements officiels de l’IRM.</div>',unsafe_allow_html=True)
