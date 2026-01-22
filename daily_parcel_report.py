import os
import requests
from supabase import create_client

# --- CONFIGS ---
PARCEL_DISCORD_URL = os.environ.get('PARCEL_DISCORD_URL') 
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
TRACK17_KEY = os.environ.get('TRACK17_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_discord_message(content):
    requests.post(PARCEL_DISCORD_URL, json={"content": content})

def run_daily_report():
    # fetch all parcels
    response = supabase.table('parcels').select("*").execute()
    parcels = response.data

    if not parcels:
        print("No parcels to report. Exiting.")
        return # Send nothing if empty

    # ask 17Track for latest info
    payload = [{"number": p['tracking_number']} for p in parcels]
    headers = {"17token": TRACK17_KEY, "Content-Type": "application/json"}
    
    try:
        resp = requests.post("https://api.17track.net/track/v2.2/gettrackinfo", json=payload, headers=headers)
        data = resp.json()
        track_infos = data.get("data", {}).get("accepted", [])
    except Exception as e:
        print(f"API Error: {e}")
        return

    # build the Report
    message_lines = []
    ids_to_delete = []

    for info in track_infos:
        number = info.get("number")
        # Get status (10=InTransit, 40=Delivered)
        status_stage = info.get("track_info", {}).get("latest_status", {}).get("status")
        
        # Get latest event description
        events = info.get("track_info", {}).get("latest_event", {})
        location = events.get("location", "")
        detail = events.get("context", "No details")

        # Map status to Emoji
        status_emoji = "🚚"
        if status_stage == 10: status_emoji = "🚛" # In Transit
        if status_stage == 30: status_emoji = "📦" # Pick Up
        if status_stage == 40: status_emoji = "✅" # Delivered
        if status_stage == 50: status_emoji = "⚠️" # Alert

        # Add line to report
        line = f"{status_emoji} **`{number}`**: {detail} "
        if location:
            line += f"({location})"
        
        message_lines.append(line)

        # auto-Delete Logic
        if status_stage == 40: # 40 = Delivered
            ids_to_delete.append(number)

    # send Report
    if message_lines:
        final_msg = "**📦 Daily Parcel Summary**\n" + "\n".join(message_lines)
        
        if ids_to_delete:
            final_msg += "\n\n🧹 **Auto-Cleaning:** Delivered parcels have been removed from the list."

        send_discord_message(final_msg)

    # execute Deletion
    if ids_to_delete:
        for num in ids_to_delete:
            supabase.table('parcels').delete().eq('tracking_number', num).execute()
            print(f"Deleted {num} from DB.")

if __name__ == "__main__":
    run_daily_report()
