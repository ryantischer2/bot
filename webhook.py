from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/lux_oscillator', methods=['POST'])
def lux_oscillator_webhook():
    data = request.json
    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_oscillator_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f)
    
    return jsonify({'status': 'success'}), 200

@app.route('/lux_price_action', methods=['POST'])
def lux_price_action_webhook():
    data = request.json
    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_price_action_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f)
    
    return jsonify({'status': 'success'}), 200

@app.route('/lux_trendcatcher', methods=['POST'])
def lux_trendcatcher_webhook():
    data = request.json
    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_trendcatcher_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f)
    
    return jsonify({'status': 'success'}), 200

@app.route('/lux_exits', methods=['POST'])
def lux_exits_webhook():
    data = request.json
    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_exits_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f)
    
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
