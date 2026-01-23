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
    if not PARCEL_DISCORD_URL:
        print("Error: No Discord Webhook URL found.")
        return
    requests.post(PARCEL_DISCORD_URL, json={"content": content})

def run_daily_report():
    print("Running Daily Parcel Report...")

    # Fetch all parcels
    response = supabase.table('parcels').select("*").execute()
    parcels = response.data

    if not parcels:
        print("No parcels to report. Exiting.")
        return 

    for p in parcels:
        if p.get('tracking_number'):
            p['tracking_number'] = p['tracking_number'].strip().upper()

    # Ask 17Track for latest info
    payload = [{"number": p['tracking_number']} for p in parcels]
    headers = {"17token": TRACK17_KEY, "Content-Type": "application/json"}
    
    url = "https://api.17track.net/track/v2.2/gettrackinfo"
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        api_data = resp.json()
        
        if api_data.get("code") != 0:
            print(f"API Error: {api_data.get('message')}")
            return
            
        raw_data = api_data.get("data", [])
        if isinstance(raw_data, dict):
            print("Warning: Received Dict instead of List. Attempting to fix...")
            track_infos = raw_data.get("accepted", []) 
        else:
            track_infos = raw_data
        
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    # Build the Report
    message_lines = []
    ids_to_delete = []

    for info in track_infos:
        # Double check info is a dict
        if isinstance(info, str):
            print(f"Skipping invalid item: {info}")
            continue

        number = info.get("number")
        
        track_info = info.get("track_info") or {}
        latest_event = track_info.get("latest_event") or {}
        latest_status = track_info.get("latest_status") or {}
        
        # Get Description (e.g. "Arrived at Sorting Center")
        description = latest_event.get("context")
        
        if not description:
            description = latest_event.get("status_description")
            
        # Get Stage Code & SubStatus
        stage = latest_status.get("status")
        sub_stage = latest_status.get("subStatus")

        # Fallback 
        if not description:
            if stage == 0: 
                if sub_stage == "NotFound":
                    description = "Registered (Waiting for Carrier Scan)"
                else:
                    description = "Registered (System Processing)"
            elif stage == 10: description = "In Transit (Moving)"
            elif stage == 30: description = "Out for Delivery / Pickup"
            elif stage == 40: description = "Delivered Successfully"
            elif stage == 50: description = "Alert: Check Courier Website"
            else: 
                # Last resort if even the stage is weird
                description = f"Status Unknown: {stage}"

        location = latest_event.get("location")
        
        # Combine: "Description, Location" or just "Description"
        if location:
            final_desc = f"{description}, {location}"
        else:
            final_desc = description

        # Emoji
        emoji = "🚚"
        if stage == 0: emoji = "📮"
        if stage == 30: emoji = "📦"
        if stage == 40: emoji = "✅"
        if stage == 50: emoji = "⚠️"

        line = f"{emoji} `{number}` : {final_desc}"
        message_lines.append(line)

        # Mark for deletion if Delivered
        if stage == 40:
            ids_to_delete.append(number)

    # Send Report
    if message_lines:
        final_msg = "**🌅 Daily Parcel Summary**\n" + "\n".join(message_lines)
        if ids_to_delete:
            final_msg += "\n\n🧹 **Auto-Cleaning:** Delivered parcels have been removed."
        send_discord_message(final_msg)
        print("Report sent to Discord.")
    else:
        print("No info found to report.")

    # Cleanup
    if ids_to_delete:
        for num in ids_to_delete:
            supabase.table('parcels').delete().eq('tracking_number', num).execute()
            print(f"Removed {num}")

if __name__ == "__main__":
    run_daily_report()
