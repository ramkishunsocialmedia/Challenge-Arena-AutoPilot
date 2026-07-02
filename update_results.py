import os
import json
import time
import requests
import gspread
from google.oauth2.service_account import Credentials

print("🏆 Winner Check System Started...")

# 1. Google Sheet se connection
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ.get("GCP_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

# Sheet ka naam "Two Players" aur tab ka naam "Matches"
sheet = client.open("Two Players").worksheet("Matches")
all_data = sheet.get_all_records()

# 2. CricAPI se matches ka current status lana
API_KEY = os.environ.get("SPORTS_API_KEY")
url = f"https://api.cricapi.com/v1/matches?apikey={API_KEY}&offset=0"

response = requests.get(url)
data = response.json()

if data.get("status") != "success":
    print("API Error:", data)
    exit()

api_matches = {m["id"]: m for m in data.get("data", [])}

# 3. Sheet ko check karna aur Result update karna
updated_count = 0
for i, row in enumerate(all_data):
    row_index = i + 2  # Sheet me data Row 2 se shuru hota hai
    match_id = str(row.get("Match ID", ""))
    current_status = str(row.get("Match Status", ""))
    
    # Agar match pehle se completed hai, to skip karein
    if current_status == "Completed":
        continue
        
    # Agar ye match API ke latest data me maujood hai
    if match_id in api_matches:
        match_info = api_matches[match_id]
        api_status = str(match_info.get("status", ""))
        match_ended = match_info.get("matchEnded", False)
        
        if match_ended:
            winner = ""
            # Status line se winner ka naam nikalna (eg: "India won by 10 runs")
            if "won by" in api_status.lower():
                winner = api_status.lower().split(" won by ")[0].title().strip()
            elif "won" in api_status.lower():
                winner = api_status.lower().split(" won ")[0].title().strip()
            elif "tied" in api_status.lower() or "draw" in api_status.lower() or "no result" in api_status.lower():
                winner = "Draw / No Result"
            else:
                winner = api_status  # Kuch samajh na aaye to pura status likh do
            
            print(f"✅ Match Ended! ID: {match_id} | Winner: {winner}")
            
            # Sheet me Update: F (6) column me Status, G (7) column me Winner
            sheet.update_cell(row_index, 6, "Completed")
            sheet.update_cell(row_index, 7, winner)
            
            updated_count += 1
            time.sleep(1.5)  # Google API ko block hone se bachane ke liye thoda break

print(f"🎉 Total {updated_count} matches update kiye gaye!")
print("Task Finished.")
