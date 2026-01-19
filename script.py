import os
import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta
from supabase import create_client

# configs from github secrets
discord_url = os.environ.get('DISCORD_URL')
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')

supabase = create_client(supabase_url, supabase_key)

# fetch stocks from supabase db
response = supabase.table('stocks').select("*").order('bucket').execute()
db_stocks = response.data

# separate bucket based on db
bucket_a = []
bucket_b = []

for item in db_stocks:
    stock_data = {
        'symbol': item['symbol'],
        'target': float(item['target_price'])
    }
    if item['bucket'] == 'A':
        bucket_a.append(stock_data)
    else:
        bucket_b.append(stock_data)

# function to send message to discord
def send_discord_message(message):
    data = {"content": message}
    response = requests.post(discord_url, json=data)
    if response.status_code != 204:
        print(f"error: {response.status_code} - {response.text}")

# function to process a list of stocks
def process_bucket(stock_list):
    report = ""
    alerts = ""
    
    for stock in stock_list:
        ticker = stock['symbol']
        target = stock['target']
        
        try:
            # fetch stock info
            ticker_obj = yf.Ticker(ticker)
            # use fast_info for speed
            info = ticker_obj.fast_info
            current_price = info.last_price
            previous_price = info.previous_close
            
            # fallback logic if fast_info fails
            if current_price is None:
                full_info = ticker_obj.info
                current_price = full_info.get('currentPrice') or full_info.get('regularMarketPrice')
                previous_price = full_info.get('previousClose')
            
            if current_price is None or previous_price is None:
                report += f"{ticker}: ⚠️ no data\n"
                continue
                
            # calculate movement
            emoji = ""
            percent = 0.0
            if current_price > previous_price:
                percent = ((current_price / previous_price) * 100) - 100
                emoji = f"🔼{percent:.2f}%"
            elif current_price < previous_price:
                percent = ((previous_price / current_price) * 100) - 100
                emoji = f"🔽{percent:.2f}%"
            else:
                emoji = "➖0.00%"
                
            report += f"{ticker}: {current_price:.2f}   {emoji}\n"
            
            # check for buy zone
            if current_price < target:
                alerts += f"🚨 alert! {ticker} is in the buy zone.\ncurrent price: {current_price:.2f}\nbuy zone: {target:.2f}\n\n"
                
        except Exception as e:
            print(f"error processing {ticker}: {e}")
            report += f"{ticker}: ⚠️ error\n"
            
    return report, alerts

# process both buckets
msg_a, alert_a = process_bucket(bucket_a)
msg_b, alert_b = process_bucket(bucket_b)

# compile final message
timestamp = datetime.now(tz=timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")
final_message = f"""Price Report ({timestamp})

----------- Bucket A: Proven Stocks (No Risk) -------------
{msg_a if msg_a else "no stocks in bucket a."}

----------- Bucket B: Diamonds(?) (High-Risk) -------------
{msg_b if msg_b else "no stocks in bucket b."}

{alert_a}{alert_b}
"""

# send to discord (split if too long)
if len(final_message) > 2000:
    send_discord_message(final_message[:2000])
    send_discord_message(final_message[2000:])
else:
    send_discord_message(final_message)