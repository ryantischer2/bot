import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import pandas_ta as ta  # Correct import for pandas_ta
from bs4 import BeautifulSoup
import re
from scipy.stats import linregress
import os

# Placeholders for API keys - user must fill these
TRADIER_TOKEN = 'YOUR_TRADIER_ACCESS_TOKEN'  # Get from https://tradier.com/
XAI_API_KEY = 'YOUR_XAI_API_KEY'  # From https://x.ai/api
DISCORD_WEBHOOK = 'https://discord.com/api/webhooks/1004251942270279721/K4GoV-q5s3JHVU5igmpA_oTeryWsYGPBDKU3peL9DkT4H2JSzb1zGEeI9d3_PxsH6BdU'
TRADERSPOST_WEBHOOK = 'https://webhooks.traderspost.io/trading/webhook/30aa3729-a189-4dda-8ddf-62d7fba63ac0/a5011e30a9f047f18fa12645953663d9'

# Headers for Tradier API
tradier_headers = {
    'Authorization': f'Bearer {TRADIER_TOKEN}',
    'Accept': 'application/json'
}

# Position tracking (simple in-memory; for production, use a file or DB)
current_position = None  # {'type': 'long' or 'short', 'entry_price': float, 'contracts': 10}
position_file = 'position.json'  # For persistence across runs

# Market data storage
market_data_file = 'market_data.csv'

# LuxAlgo oscillator alerts daily file
today_date = datetime.now().strftime('%Y-%m-%d')
lux_oscillator_file = f'lux_oscillator_{today_date}.json'
lux_price_action_file = f'lux_price_action_{today_date}.json'

def load_position():
    try:
        with open(position_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError, ValueError):
        return None  # Handle empty/invalid file

def save_position(pos):
    with open(position_file, 'w') as f:
        json.dump(pos, f)

current_position = load_position()

def append_market_data(df_new):
    """Append new data to daily CSV"""
    if os.path.exists(market_data_file):
        df_old = pd.read_csv(market_data_file)
        df = pd.concat([df_old, df_new]).drop_duplicates(subset='date', keep='last')
    else:
        df = df_new
    df.to_csv(market_data_file, index=False)

def erase_market_data():
    """Erase market data at end of day"""
    if os.path.exists(market_data_file):
        os.remove(market_data_file)

def get_tradier_quotes(symbols):
    """Fetch real-time quotes for symbols like SPY, ^VIX"""
    url = 'https://api.tradier.com/v1/markets/quotes'
    params = {'symbols': ','.join(symbols)}
    response = requests.get(url, headers=tradier_headers, params=params)
    return response.json()['quotes']['quote'] if response.ok else None

def get_tradier_history(symbol, interval='1min', start=None, end=None):
    """Fetch intraday history for anchored VWAP calculation"""
    url = 'https://api.tradier.com/v1/markets/history'
    if not start:
        today = datetime.now().date()
        start = (today - timedelta(days=30)).strftime('%Y-%m-%d')  # Fetch last 30 days for EMA
        end = datetime.now().strftime('%Y-%m-%d %H:%M')
    params = {'symbol': symbol, 'interval': interval, 'start': start, 'end': end}
    response = requests.get(url, headers=tradier_headers, params=params)
    data = response.json()['history']['day'] if response.ok else []
    return pd.DataFrame(data)  # Columns: date, open, high, low, close, volume

def compute_anchored_vwap(df, anchor_time='09:33'):
    """Compute anchored VWAP from first 3-min (aggregate first 3 bars)"""
    df['timestamp'] = pd.to_datetime(df['date'])
    df = df.sort_values('timestamp')
    # Aggregate first 3 min if needed (assuming 1min bars)
    first_three = df.iloc[0:3]
    anchor_close = first_three['close'].mean()  # Simple approx; adjust
    anchor_idx = df[df['timestamp'] >= pd.to_datetime(anchor_time)].index[0]
    df_post = df.iloc[anchor_idx:]
    typical_price = (df_post['high'] + df_post['low'] + df_post['close']) / 3
    pv = typical_price * df_post['volume']
    df_post['vwap'] = pv.cumsum() / df_post['volume'].cumsum()
    # Bands: ±3 SD
    df_post['sd'] = (typical_price - df_post['vwap']).rolling(20).std()
    df_post['upper3'] = df_post['vwap'] + 3 * df_post['sd']
    df_post['lower3'] = df_post['vwap'] - 3 * df_post['sd']
    df_post['upper2'] = df_post['vwap'] + 2 * df_post['sd']
    df_post['lower2'] = df_post['vwap'] - 2 * df_post['sd']
    # Slope over last 10 bars
    recent_vwap = df_post['vwap'].tail(10)
    slope = np.polyfit(range(len(recent_vwap)), recent_vwap, 1)[0]
    return df_post.iloc[-1], slope  # Current row, slope

def compute_indicators(df):
    """Compute RSI, MACD, ATR, etc. using pandas-ta or manual"""
    # Assuming pandas-ta installed; else implement
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    df['ema_21'] = ta.core.ema(df['close'], length=21)
    return df.iloc[-1]  # Current values

def calculate_trend_channel(df, period=20):
    """Calculate simple linear regression trend channel"""
    df = df.tail(period)  # Last N bars
    x = np.arange(len(df))
    
    # Upper channel: regression on highs
    slope_high, intercept_high, _, _, _ = linregress(x, df['high'])
    upper = slope_high * x + intercept_high
    
    # Lower channel: regression on lows
    slope_low, intercept_low, _, _, _ = linregress(x, df['low'])
    lower = slope_low * x + intercept_low
    
    # Main trend on closes for direction
    slope_close, intercept_close, _, _, _ = linregress(x, df['close'])
    
    # Current price relation
    current_price = df['close'].iloc[-1]
    current_upper = upper[-1]
    current_lower = lower[-1]
    
    if slope_close > 0:
        channel_type = 'bullish'
    elif slope_close < 0:
        channel_type = 'bearish'
    else:
        channel_type = 'neutral'
    
    if current_price > current_upper:
        status = f'exited above {channel_type} channel'
    elif current_price < current_lower:
        status = f'exited below {channel_type} channel'
    else:
        status = f'within {channel_type} channel'
    
    return status

def get_fundamentals():
    """Fetch S&P 500 fundamentals from free web sources"""
    # P/E Ratio from multpl.com
    try:
        url = 'https://www.multpl.com/s-p-500-pe-ratio'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        pe_ratio = float(soup.find('div', id='current').text.strip().split()[0])
    except:
        pe_ratio = 25.0  # Fallback

    # Dividend Yield from multpl.com
    try:
        url = 'https://www.multpl.com/s-p-500-dividend-yield'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        dividend_yield = float(soup.find('div', id='current').text.strip().split()[0])
    except:
        dividend_yield = 1.5  # Fallback

    # Sector Weights approximation (by count of companies, not market cap) from Wikipedia
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        df = pd.read_html(url)[0]
        sector_counts = df['GICS Sector'].value_counts(normalize=True) * 100
        sector_weights = ', '.join([f"{sector}: {weight:.1f}%" for sector, weight in sector_counts.items()])
    except:
        sector_weights = "Technology: 30%, Financials: 15%"  # Fallback

    return pe_ratio, dividend_yield, sector_weights

def get_macro():
    """Fetch macro data from free web sources"""
    # Fed Funds Rate from FRED
    try:
        url = 'https://fred.stlouisfed.org/series/FEDFUNDS'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        fed_rate = float(soup.find('span', {'class': 'series-meta-observation-value'}).text.strip())
    except:
        fed_rate = 5.25  # Fallback

    # CPI YoY from BLS
    try:
        url = 'https://www.bls.gov/cpi/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        match = re.search(r'rose (\d\.\d) percent over the last 12 months', text)
        if match:
            cpi = float(match.group(1))
        else:
            raise ValueError("No match")
    except:
        cpi = 3.2  # Fallback

    # 10Y Treasury Yield from Treasury.gov
    try:
        current_month = datetime.now().strftime('%Y%m')
        url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value_month={current_month}'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        last_row = soup.find_all('tr')[-1]
        tds = last_row.find_all('td')
        treasury_yield = float(tds[12].text)
    except:
        treasury_yield = 4.2  # Fallback

    return fed_rate, cpi, treasury_yield

def get_sentiment():
    """Load LuxAlgo alerts from JSON file and format for prompt"""
    try:
        with open('/home/ryan_tischer/luxdata.json', 'r') as f:
            data = json.load(f)
        # Extract trend catcher for various time frames
        time_frames = ['1min', '3min', '5min', '10min', '30min', '1h']
        trend_catcher = ', '.join([f"{tf}: {data.get(f'trend_catcher_{tf.replace('min', '') if 'min' in tf else tf}', 'N/A')}" for tf in time_frames])
        # Extract other data
        broken_trendline = data.get('broken_trendline', 'N/A')
        order_blocks = data.get('order_blocks', {'bullish': 'N/A', 'bearish': 'N/A'})
        order_blocks_str = f"Bullish: {order_blocks.get('bullish', 'N/A')}, Bearish: {order_blocks.get('bearish', 'N/A')}"
        # Extract exits (now as lists)
        exit_frames = ['3min', '5min', '15min', '30min']
        exits = ', '.join([f"{tf}: {', '.join(data.get(f'exits_{tf}', [])) if isinstance(data.get(f'exits_{tf}'), list) else data.get(f'exits_{tf}', 'N/A')}" for tf in exit_frames])
        return f"LuxAlgo Trend Catcher: {trend_catcher}; Broken Trendline: {broken_trendline}; Order Blocks: {order_blocks_str}; Exits: {exits}"
    except Exception as e:
        return "No LuxAlgo data available"

def get_oscillator_alerts():
    """Load daily LuxAlgo oscillator matrix alerts and format with timestamps"""
    try:
        with open(lux_oscillator_file, 'r') as f:
            alerts = json.load(f)
        formatted = []
        for alert in alerts:
            ts = datetime.fromtimestamp(alert['bartime'] / 1000).strftime('%Y-%m-%d %H:%M:%S') if 'bartime' in alert else 'N/A'
            formatted.append(f"Alert: {alert.get('alert', 'N/A')}, TF: {alert.get('tf', 'N/A')}, OHLCV: O={alert['ohlcv'].get('open', 'N/A')}, H={alert['ohlcv'].get('high', 'N/A')}, L={alert['ohlcv'].get('low', 'N/A')}, C={alert['ohlcv'].get('close', 'N/A')}, V={alert['ohlcv'].get('volume', 'N/A')}, Time: {ts}")
        return '; '.join(formatted) if formatted else "No oscillator alerts today"
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return "No oscillator alerts today"

def get_price_action_alerts():
    """Load daily LuxAlgo price action concepts alerts and format with timestamps"""
    try:
        with open(lux_price_action_file, 'r') as f:
            alerts = json.load(f)
        formatted = []
        for alert in alerts:
            ts = datetime.fromtimestamp(alert['bartime'] / 1000).strftime('%Y-%m-%d %H:%M:%S') if 'bartime' in alert else 'N/A'
            formatted.append(f"Alert: {alert.get('alert', 'N/A')}, TF: {alert.get('tf', 'N/A')}, OHLCV: O={alert['ohlcv'].get('open', 'N/A')}, H={alert['ohlcv'].get('high', 'N/A')}, L={alert['ohlcv'].get('low', 'N/A')}, C={alert['ohlcv'].get('close', 'N/A')}, V={alert['ohlcv'].get('volume', 'N/A')}, Time: {ts}")
        return '; '.join(formatted) if formatted else "No price action alerts today"
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return "No price action alerts today"

def get_historical_context(df):
    """Simple historical avg"""
    prev_day_high = df['high'].max()  # Approx
    prev_day_low = df['low'].min()
    return prev_day_high, prev_day_low

def get_candle_patterns(df):
    """Detect patterns like engulfing"""
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    if last_candle['close'] > prev_candle['open'] and last_candle['open'] < prev_candle['close']:  # Bullish engulfing approx
        pattern = "bullish engulfing"
    elif last_candle['close'] < prev_candle['open'] and last_candle['open'] > prev_candle['close']:  # Bearish engulfing approx
        pattern = "bearish engulfing"
    else:
        pattern = "none"
    return pattern

def build_prompt(current_data, slope, indicators, vix, fundamentals, macro, sentiment, oscillator_alerts, price_action_alerts, historical, candle, time_of_day, channel_1min, channel_30min):
    pe, div_yield, sectors = fundamentals
    fed, cpi, treasury = macro
    prev_high, prev_low = historical
    # Add price interaction with bands
    current_price = current_data['close']
    lower_band = current_data['lower3']
    upper_band = current_data['upper3']
    interaction = ""
    if abs(current_price - lower_band) < 0.5:  # Threshold for 'interaction', adjust as needed
        interaction = "interacting with lower outer band"
    elif abs(current_price - upper_band) < 0.5:
        interaction = "interacting with upper outer band"
    # Add existing position info
    position_info = "No open position."
    if current_position:
        position_info = f"Current open position: {current_position['type']} with {current_position['contracts']} contracts entered at {current_position['entry_price']}."
    # Add EMA info
    ema_21 = indicators['ema_21']
    ema_relation = "above" if current_price > ema_21 else "below" if current_price < ema_21 else "at"
    # Introduction
    intro = "You are a professional day trader with years of experience in SPY options, focused on generating consistent profits to support a charitable organization dedicated to education for underprivileged children. Your decisions prioritize high-confidence setups, risk management, and ethical trading to maximize returns for good."
    prompt = f"""
{intro}
Analyze SPY for trading signal:
Current price: {current_price} ({interaction})
Anchored VWAP (from 09:33): {current_data['vwap']}
Outermost bands: Upper {upper_band}, Lower {lower_band}
Second bands: Upper {current_data['upper2']}, Lower {current_data['lower2']}
VWAP slope: {slope} (positive=up, negative=down)
RSI: {indicators['rsi']}
MACD: {indicators['macd']}, Signal: {indicators['macd_signal']}, Hist: {indicators['macd_hist']}
ATR: {indicators['atr']}
VIX: {vix}
S&P P/E: {pe}, Dividend Yield: {div_yield}, Sectors: {sectors}
Fed Rate: {fed}, CPI: {cpi}, 10Y Treasury: {treasury}
LuxAlgo Alerts: {sentiment}
LuxAlgo Oscillator Matrix Alerts (with timestamps): {oscillator_alerts}
LuxAlgo Price Action Concepts Alerts (with timestamps): {price_action_alerts}
Prev day high/low: {prev_high}/{prev_low}
Candle pattern: {candle}
Time: {time_of_day}
{position_info}
Price relative to 21-day EMA: {ema_relation} (EMA value: {ema_21})
1min channel: {channel_1min}
30min channel: {channel_30min}

Strategy: Trade when price interacts with outer band VWAP (touches or approaches) and shows bullish candle behavior for long (e.g., engulfing, hammer) or bearish for short (e.g., shooting star, engulfing). Only 8:30 CT - noon CT.
Give heavy consideration to LuxAlgo data (trend catcher across timeframes, broken trendlines, order blocks), oscillator matrix alerts (with their timestamps and OHLCV), and price action concepts data (with their timestamps and OHLCV) when deciding entries/exits. For exits, place more emphasis on signals from higher time frames (e.g., 15min and 30min over 3min and 5min). Handle multiple exit signals per timeframe (common on shorter frames like 3min/5min with 2-3 signals, vs. once on longer like 15min/30min) by considering persistence or the latest signal. Consider existing positions and decide if to close them based on the data. Favor longs if above 21-day EMA, shorts if below. Consider if price is within or exited a bullish/bearish channel on 1min and 30min timeframes.
Enter long on lower band interaction with bullish candle, short on upper with bearish candle.
Exit on opposite band touch unless slope favors your direction, then hold until second band break or trend flip.
Return only: 'long', 'short', 'close long', or 'close short'. High confidence only.
"""
    return prompt

def send_to_xai(prompt):
    url = 'https://api.x.ai/v1/chat/completions'  # Assumed endpoint
    headers = {'Authorization': f'Bearer {XAI_API_KEY}', 'Content-Type': 'application/json'}
    data = {
        'model': 'grok-4',
        'messages': [{'role': 'user', 'content': prompt}]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        return response.json()['choices'][0]['message']['content'].strip()
    return None

def send_to_discord(message):
    data = {'content': message}
    requests.post(DISCORD_WEBHOOK, json=data)

def send_to_traderspost(action, quantity=None):
    if action == "exit":
        payload = {
            "ticker": "SPY",
            "action": "exit"
        }
    else:
        payload = {
            "ticker": "SPY",
            "action": action,
            "quantity": quantity if quantity else 10
        }
    response = requests.post(TRADERSPOST_WEBHOOK, json=payload)
    if response.ok:
        print("Sent to TradersPost successfully")
    else:
        print(f"Failed to send to TradersPost: {response.text}")

def handle_signal(signal, spy_price, time_of_day):
    global current_position
    if signal == 'long':
        if current_position is None:
            current_position = {'type': 'long', 'entry_price': spy_price, 'contracts': 10}
            save_position(current_position)
            send_to_discord(f"Entered LONG at {spy_price} - Time: {time_of_day}")
            send_to_traderspost("buy")
    elif signal == 'short':
        if current_position is None:
            current_position = {'type': 'short', 'entry_price': spy_price, 'contracts': 10}
            save_position(current_position)
            send_to_discord(f"Entered SHORT at {spy_price} - Time: {time_of_day}")
            send_to_traderspost("buy")
    elif signal == 'close long' and current_position and current_position['type'] == 'long':
        send_to_discord(f"Closed LONG at {spy_price} - Time: {time_of_day}")
        send_to_traderspost("exit")
        current_position = None
        save_position(current_position)
    elif signal == 'close short' and current_position and current_position['type'] == 'short':
        send_to_discord(f"Closed SHORT at {spy_price} - Time: {time_of_day}")
        send_to_traderspost("exit")
        current_position = None
        save_position(current_position)

def monitor_position(spy_price, time_of_day):
    global current_position
    if current_position:
        entry_price = current_position['entry_price']
        pos_type = current_position['type']
        price_change = spy_price - entry_price if pos_type == 'long' else entry_price - spy_price
        if abs(price_change) >= 2:
            # Sell half contracts
            half = current_position['contracts'] // 2
            current_position['contracts'] = half
            save_position(current_position)
            send_to_discord(f"Sold half contracts ({current_position['contracts']} remaining) for {pos_type.upper()} due to $2 price change. Current SPY: {spy_price} - Time: {time_of_day}")
            send_to_traderspost("sell", half)

def monitor_stop_loss(spy_price, time_of_day, atr):
    global current_position
    if current_position:
        entry_price = current_position['entry_price']
        pos_type = current_position['type']
        stop_loss = entry_price - (atr * 2) if pos_type == 'long' else entry_price + (atr * 2)  # Example: 2x ATR stop
        if (pos_type == 'long' and spy_price <= stop_loss) or (pos_type == 'short' and spy_price >= stop_loss):
            send_to_discord(f"Stop loss hit for {pos_type.upper()} at {spy_price} - Time: {time_of_day}")
            send_to_traderspost("exit")
            current_position = None
            save_position(current_position)

# Main loop (run every 1 min during market hours)
while True:
    now = datetime.now()
    if now.hour >= 9 and now.hour < 16:  # ET market hours approx
        # Fetch data
        quotes = get_tradier_quotes(['SPY', '^VIX'])
        if not quotes:
            time.sleep(60)
            continue
        spy_quote = quotes[0] if quotes[0]['symbol'] == 'SPY' else quotes[1]
        spy_price = spy_quote['last']
        vix = quotes[1]['last'] if quotes[1]['symbol'] == '^VIX' else quotes[0]['last']
        
        df_1min = get_tradier_history('SPY', interval='1min')
        if df_1min.empty:
            time.sleep(60)
            continue
        
        append_market_data(df_1min)  # Collect data
        
        df_30min = get_tradier_history('SPY', interval='30min')
        
        current_data, slope = compute_anchored_vwap(df_1min)
        indicators = compute_indicators(df_1min)
        channel_1min = calculate_trend_channel(df_1min)
        channel_30min = calculate_trend_channel(df_30min)
        fundamentals = get_fundamentals()
        macro = get_macro()
        sentiment = get_sentiment()
        oscillator_alerts = get_oscillator_alerts()
        price_action_alerts = get_price_action_alerts()
        historical = get_historical_context(df_1min.shift(periods=1))  # Approx prev day
        candle = get_candle_patterns(df_1min)
        time_of_day = now.strftime('%H:%M ET')
        
        # Check for stop loss every poll
        monitor_stop_loss(spy_price, time_of_day, indicators['atr'])
        
        # Only query AI between 9:45 and 12:00 ET
        if now.hour == 9 and now.minute >= 45 or now.hour == 10 or now.hour == 11 or (now.hour == 12 and now.minute == 0):
            prompt = build_prompt(current_data, slope, indicators, vix, fundamentals, macro, sentiment, oscillator_alerts, price_action_alerts, historical, candle, time_of_day, channel_1min, channel_30min)
            
            signal = send_to_xai(prompt)
            if signal in ['long', 'short', 'close long', 'close short']:
                send_to_discord(f"AI Signal: {signal} at {time_of_day} - SPY Price: {spy_price}")
                handle_signal(signal, spy_price, time_of_day)
            
            # At noon, close if open
            if now.hour == 12 and now.minute == 0 and current_position:
                signal_close = 'close long' if current_position['type'] == 'long' else 'close short'
                handle_signal(signal_close, spy_price, time_of_day)
        
        # Monitor for price change exit
        monitor_position(spy_price, time_of_day)
    
    elif now.hour >= 16:  # After market close, erase data
        erase_market_data()
    
    time.sleep(60)  # Poll every minute
