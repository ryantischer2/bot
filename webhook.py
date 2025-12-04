from flask import Flask, request, jsonify, abort
import json
from datetime import datetime
import os

app = Flask(__name__)

# Whitelist of allowed IP addresses (TradingView webhook IPs)
ALLOWED_IPS = [
    '52.89.214.238',
    '34.212.75.30',
    '54.218.53.128',
    '52.32.178.7'
]

def check_ip():
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        abort(403)  # Forbidden if IP not in whitelist

@app.before_request
def limit_remote_addr():
    check_ip()

@app.route('/lux_oscillator', methods=['POST'])
def lux_oscillator_webhook():
    if request.is_json:
        data = request.get_json()
    else:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except json.JSONDecodeError:
            return jsonify({'error': 'invalid json'}), 400
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
    if request.is_json:
        data = request.get_json()
    else:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except json.JSONDecodeError:
            return jsonify({'error': 'invalid json'}), 400
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
    if request.is_json:
        data = request.get_json()
    else:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except json.JSONDecodeError:
            return jsonify({'error': 'invalid json'}), 400
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
    if request.is_json:
        data = request.get_json()
    else:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except json.JSONDecodeError:
            return jsonify({'error': 'invalid json'}), 400
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
    app.run(host='0.0.0.0', port=80)
