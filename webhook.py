#!/usr/bin/env python3
from flask import Flask, request, jsonify, abort
import json
from datetime import datetime
import os

app = Flask(__name__)

# TradingView official webhook IPs — whitelist
ALLOWED_IPS = [
    '52.89.214.238',
    '34.212.75.30',
    '54.218.53.128',
    '52.32.178.7'
]

def check_ip():
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        print(f"Blocked unauthorized IP: {client_ip}")
        abort(403)

@app.before_request
def limit_remote_addr():
    check_ip()

def parse_payload():
    """Parse both proper JSON and TradingView's text/plain payloads"""
    raw = request.data.decode('utf-8', errors='ignore').strip()
    print(f"RAW PAYLOAD ({len(raw)} chars): {raw}")

    if not raw:
        print("ERROR: Empty payload received")
        return None

    # Try parsing as JSON directly (this works for 99% of your real alerts)
    try:
        parsed = json.loads(raw)
        print(f"Successfully parsed JSON: {parsed}")
        return parsed
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        pass

    # Fallback: some LuxAlgo alerts send just a plain string
    # Example: "Within Bullish Block"
    if raw and raw[0] not in ['{', '[']:
        fallback = {
            "alert": raw.strip(),
            "ticker": "SPY",
            "tf": "unknown",
            "bartime": int(datetime.now().timestamp() * 1000)
        }
        print(f"Using fallback format: {fallback}")
        return fallback

    print(f"ERROR: Could not parse payload: {raw[:200]}")
    return None

def save_alert(data, prefix):
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'{prefix}_{today}.json'
    path = os.path.join('/home/ryan_tischer/bot', filename)

    if os.path.exists(path):
        with open(path, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []

    alerts.append(data)

    with open(path, 'w') as f:
        json.dump(alerts, f, indent=2)

    print(f"Saved to {filename} — total alerts: {len(alerts)}")

@app.route('/lux_oscillator', methods=['POST'])
def lux_oscillator():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400
    save_alert(data, 'lux_oscillator')
    return jsonify({'status': 'success'}), 200

@app.route('/lux_price_action', methods=['POST'])
def lux_price_action():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400
    save_alert(data, 'lux_price_action')
    return jsonify({'status': 'success'}), 200

@app.route('/lux_trendcatcher', methods=['POST'])
def lux_trendcatcher():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400
    save_alert(data, 'lux_trendcatcher')
    return jsonify({'status': 'success'}), 200

@app.route('/lux_exits', methods=['POST'])
def lux_exits():
    data = parse_payload()
    if not data:
        return jsonify({'error': 'invalid payload'}), 400
    save_alert(data, 'lux_exits')
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    # Runs on port 80 with capabilities (set via setcap) or via systemd as root
    app.run(host='0.0.0.0', port=80)
