import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import os
import time

print("🚀 Auto-Pilot System Started...")

# 1. Google Sheets Authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get('GCP_CREDENTIALS')

if not creds_json:
    print("❌ Error: GCP_CREDENTIALS secret is missing!")
    exit()

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 2. Google Sheet खोलना
try:
    sheet = client.open("Two Players").worksheet("Matches")
    print("✅ Google Sheet Successfully Connected!")
    
    # शीट में पहले से मौजूद मैच ID निकालना (ताकि डबल एंट्री ना हो)
    existing_data = sheet.get_all_records()
    existing_match_ids = [str(row.get("Match ID", "")) for row in existing_data]
    
except Exception as e:
    print(f"❌ Sheet Error: {e}")
    exit()

# 3. Sports API से मैचों का डेटा लाना
API_KEY = os.environ.get('SPORTS_API_KEY')
url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"

print("📡 Fetching Live Matches from API...")
response = requests.get(url)
data = response.json()

# 4. नए मैचों और उनके खिलाड़ियों (Squad) को शीट में डालना
if data.get("status") == "success":
    matches = data.get("data", [])
    added_count = 0
    new_rows = []
    
    for match in matches:
        match_id = str(match.get("id"))
        
        # सिर्फ उन्हीं मैचों को प्रोसेस करेंगे जो शीट में पहले से नहीं हैं
        if match_id not in existing_match_ids:
            match_name = match.get("name")
            match_time = match.get("dateTimeGMT")
            
            teams = match.get("teams", ["Team A", "Team B"])
            team_a = teams[0] if len(teams) > 0 else "TBA"
            team_b = teams[1] if len(teams) > 1 else "TBA"

            # --- SQUAD (PLAYERS) FETCH KARNA ---
            team_a_players = "Not Announced"
            team_b_players = "Not Announced"
            
            try:
                squad_url = f"https://api.cricapi.com/v1/match_squad?apikey={API_KEY}&id={match_id}"
                squad_res = requests.get(squad_url).json()
                
                if squad_res.get("status") == "success" and squad_res.get("data"):
                    squad_data = squad_res.get("data")
                    for team_squad in squad_data:
                        t_name = team_squad.get("teamName", "")
                        players_list = team_squad.get("players", [])
                        players_names = ", ".join([p.get("name", "") for p in players_list])
                        
                        if t_name == team_a:
                            team_a_players = players_names
                        elif t_name == team_b:
                            team_b_players = players_names
                time.sleep(1) # API लिमिट से बचने के लिए 1 सेकंड का ब्रेक
            except Exception as e:
                print(f"⚠️ Squad fetch error for {match_id}: {e}")
            # ------------------------------------

            # शीट में नई लाइन (Column A से I तक)
            # Format: [ID, Name, Date, Team A, Team B, Status, Winner, Team A Players, Team B Players]
            new_row = [match_id, match_name, match_time, team_a, team_b, "Upcoming", "", team_a_players, team_b_players]
            new_rows.append(new_row)
            added_count += 1
            print(f"✅ Added Match: {team_a} vs {team_b} (Squads Included)")
    
    # एक साथ सारे नए मैचों को शीट में सेव करना (ताकि शीट फ़ास्ट काम करे)
    if new_rows:
        sheet.append_rows(new_rows)
        print(f"🎉 Success: {added_count} new matches added to the sheet!")
    else:
        print("⚡ कोई नया मैच नहीं मिला। सारे मैच पहले से शीट में अपडेटेड हैं।")
else:
    print("⚠️ API से डेटा नहीं मिला या API Key गलत है।")
