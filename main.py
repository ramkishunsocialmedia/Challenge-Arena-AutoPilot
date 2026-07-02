import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import os

print("🚀 Auto-Pilot System Started...")

# 1. Google Sheets Authentication (JSON Key GitHub Secrets से ली जाएगी)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get('GCP_CREDENTIALS')

if not creds_json:
    print("❌ Error: GCP_CREDENTIALS secret is missing!")
    exit()

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 2. आपकी Google Sheet खोलना
try:
    # ध्यान दें: आपकी शीट का नाम बिल्कुल यही होना चाहिए
    sheet = client.open("Two Players").worksheet("Matches")
    print("✅ Google Sheet Successfully Connected!")
except Exception as e:
    print(f"❌ Sheet Error: {e}")
    exit()

# 3. Sports API से आज के मैचों का डेटा लाना
API_KEY = os.environ.get('SPORTS_API_KEY')
# यहाँ हम CricAPI का उदाहरण ले रहे हैं (आप इसे बदल सकते हैं)
url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"

print("📡 Fetching Live Matches from API...")
response = requests.get(url)
data = response.json()

# 4. नए मैचों को शीट में डालना
if data.get("status") == "success":
    matches = data.get("data", [])
    added_count = 0
    
    for match in matches:
        # अगर मैच आज का है या आने वाला है (Upcoming/Live)
        match_id = match.get("id")
        match_name = match.get("name")
        match_time = match.get("dateTimeGMT")
        
        # टीम्स के नाम निकालना
        teams = match.get("teams", ["Team A", "Team B"])
        team_a = teams[0] if len(teams) > 0 else "TBA"
        team_b = teams[1] if len(teams) > 1 else "TBA"

        # शीट में नई लाइन (Row) बनाना
        new_row = [match_id, match_name, match_time, team_a, team_b, "Upcoming", ""]
        
        # शीट में डेटा सेव करना
        sheet.append_row(new_row)
        added_count += 1
        print(f"✅ Added Match: {team_a} vs {team_b}")
        
    print(f"🎉 Success: {added_count} new matches added to the sheet!")
else:
    print("⚠️ API से डेटा नहीं मिला या API Key गलत है।")
