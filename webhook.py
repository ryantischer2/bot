from flask import Flask, request, jsonify, abort
import json
from datetime import datetime
import os

app = Flask(__name__)

# TradingView webhook IPs (whitelist)
ALLOWED_IPS = [
    '52.89.214.238',
    '34.212.75.30',
    '54.218.53.128',
    '52.32.178.7'
]

def check_ip():
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        abort(403)  # Forbidden

@app.before_request
def limit_remote_addr():
    check_ip()

def parse_payload():
    """Robustly parse TradingView webhook payload (text/plain or application/json)"""
    raw = request.data.decode('utf-8').strip()
    if not raw:
        return None
    
    # Remove surrounding quotes/newlines if present
    raw = raw.strip('"\' \n\r\t')
    
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    
    # Fallback: extract JSON between first { and last }
    start = raw.find('{')
    end = raw.rfind('}') + 1
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end])
        except:
            pass
    
    print(f"JSON parse failed | Raw payload: {raw[:200]}")
    return None

@app.route('/lux_oscillator', methods=['POST'])
def lux_oscillator_webhook():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400

    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_oscillator_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return jsonify({'status': 'success'}), 200

@app.route('/lux_price_action', methods=['POST'])
def lux_price_action_webhook():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400

    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_price_action_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return jsonify({'status': 'success'}), 200

@app.route('/lux_trendcatcher', methods=['POST'])
def lux_trendcatcher_webhook():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400

    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_trendcatcher_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return jsonify({'status': 'success'}), 200

@app.route('/lux_exits', methods=['POST'])
def lux_exits_webhook():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400

    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'lux_exits_{today_date}.json'
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
    
    alerts.append(data)
    
    with open(file_name, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
