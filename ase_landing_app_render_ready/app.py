from flask import Flask, render_template, jsonify
import requests
from metar import Metar
import dateutil.parser
import time

app = Flask(__name__)
ASE = 'KASE'
AVIATIONSTACK_KEY = 'd69746ff2a8556b26834e5f3407bd394'

def get_metar():
    url = f'https://aviationweather.gov/api/data/metar?ids={ASE}&format=JSON&hoursBeforeNow=1'
    r = requests.get(url)
    if not r.ok:
        return None
    data = r.json().get('data', [])
    if not data:
        return None
    return Metar.Metar(data[0]['raw_text'])

def score_weather(m):
    score = 100
    vis = m.vis.value() / 1609 if m.vis else 10
    ws = m.wind_speed.value() if m.wind_speed else 0
    ceil = m.ceiling.value() if m.ceiling else 9999
    snow = 'SN' in m.sky_conditions if m.sky_conditions else False
    if vis < 3: score -= 25
    elif vis < 5: score -= 10
    if ws > 25: score -= 20
    elif ws > 15: score -= 10
    if ceil < 1000: score -= 20
    elif ceil < 3000: score -= 10
    if snow: score -= 15
    if m.sky_conditions and any(c in ['IFR','LIFR','OVC'] for c in m.sky_conditions):
        score -= 10
    return max(score, 0)

def get_upcoming_flights():
    url = 'http://api.aviationstack.com/v1/flights'
    params = {'access_key': AVIATIONSTACK_KEY, 'dep_iata': 'DEN', 'arr_iata': 'ASE', 'limit': 100}
    r = requests.get(url, params=params).json()
    flights = []
    now_ts = time.time()
    for f in r.get('data', []):
        sched = f.get('departure', {}).get('scheduled')
        if sched:
            dt = dateutil.parser.isoparse(sched).timestamp()
            if 0 <= dt - now_ts <= 12*3600:
                flights.append({'flight': f['flight']['iata'], 'time': sched})
    return flights

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/data')
def data():
    m = get_metar()
    wx_score = score_weather(m) if m else 0
    flights = get_upcoming_flights()
    output = [{'flight': f['flight'], 'time': f['time'][-5:], 'probability': wx_score} for f in flights]
    return jsonify(output)

if __name__ == '__main__':
    app.run(debug=True)
