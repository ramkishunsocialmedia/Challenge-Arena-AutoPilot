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
    print("❌ Error: GCP_CREDENTIALS missing!")
    exit()

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Two Players").worksheet("Matches")

# शीट का सारा डेटा एक साथ पढ़ना
existing_data = sheet.get_all_values()
# Column A से सारे Match IDs निकालना
existing_match_ids = [row[0] for row in existing_data if len(row) > 0] 

API_KEY = os.environ.get('SPORTS_API_KEY')

# ==========================================
# PART 1: पुरानी 'Not Announced' एंट्री को अपडेट करना
# ==========================================
print("🔍 Checking for 'Not Announced' squads in existing matches...")
for index, row in enumerate(existing_data):
    if index == 0: continue # Header को छोड़ दें
    
    # अगर कॉलम H और I मौजूद हैं
    if len(row) >= 9:
        match_id = row[0]
        team_a = row[3]
        team_b = row[4]
        status = row[5]
        team_a_players = row[7]
        team_b_players = row[8]
        
        # अगर मैच अभी Upcoming है और प्लेयर्स अनाउंस नहीं हुए थे
        if status == "Upcoming" and ("Not Announced" in team_a_players or "Not Announced" in team_b_players):
            print(f"🔄 Re-checking squad for: {team_a} vs {team_b}")
            try:
                squad_url = f"https://api.cricapi.com/v1/match_squad?apikey={API_KEY}&id={match_id}"
                squad_res = requests.get(squad_url).json()
                
                if squad_res.get("status") == "success" and squad_res.get("data"):
                    squad_data = squad_res.get("data")
                    new_team_a_players = "Not Announced"
                    new_team_b_players = "Not Announced"
                    
                    for team_squad in squad_data:
                        t_name = team_squad.get("teamName", "")
                        players_list = team_squad.get("players", [])
                        players_names = ", ".join([p.get("name", "") for p in players_list])
                        
                        if t_name == team_a:
                            new_team_a_players = players_names
                        elif t_name == team_b:
                            new_team_b_players = players_names
                            
                    # अगर अब नाम मिल गए हैं, तो सिर्फ उसी Cell को अपडेट करें
                    if new_team_a_players != "Not Announced" or new_team_b_players != "Not Announced":
                        row_number = index + 1 # Gspread में row 1 से शुरू होती है
                        sheet.update_cell(row_number, 8, new_team_a_players) # Column H
                        sheet.update_cell(row_number, 9, new_team_b_players) # Column I
                        print(f"✅ Squad updated in sheet for {team_a} vs {team_b}")
                time.sleep(1) # API ब्लॉक न हो इसलिए 1 सेकंड रुकना
            except Exception as e:
                print(f"⚠️ Error updating squad for {match_id}: {e}")

# ==========================================
# PART 2: नए मैच खोजना और शीट में जोड़ना
# ==========================================
print("📡 Fetching Live Matches from API...")
url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"
response = requests.get(url)
data = response.json()

if data.get("status") == "success":
    matches = data.get("data", [])
    added_count = 0
    new_rows = []
    
    for match in matches:
        match_id = str(match.get("id"))
        
        # अगर मैच शीट में नहीं है, तभी आगे बढ़ें
        if match_id not in existing_match_ids:
            match_name = match.get("name")
            match_time = match.get("dateTimeGMT")
            teams = match.get("teams", ["Team A", "Team B"])
            team_a = teams[0] if len(teams) > 0 else "TBA"
            team_b = teams[1] if len(teams) > 1 else "TBA"

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
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Squad fetch error for {match_id}: {e}")

            # नई लाइन तैयार करना
            new_row = [match_id, match_name, match_time, team_a, team_b, "Upcoming", "", team_a_players, team_b_players]
            new_rows.append(new_row)
            added_count += 1
            print(f"✅ Added New Match: {team_a} vs {team_b}")
    
    # सारे नए मैचों को एक साथ शीट में डालना
    if new_rows:
        sheet.append_rows(new_rows)
        print(f"🎉 Success: {added_count} new matches added!")
    else:
        print("⚡ No new matches found to add.")
else:
    print("⚠️ API data not found or Key is wrong.")
