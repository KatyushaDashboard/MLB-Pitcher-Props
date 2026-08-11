import requests
import json
import datetime
import os

# API Key Boss yang sudah disuntikkan
ODDS_API_KEY = "c8d93d667bf40310980a6d68e154c96f"

def get_pitcher_props():
    """Menarik Prop Lines & Odds dari The Odds API."""
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        # 5 Pasar Prop Utama Kita
        "markets": "pitcher_strikeouts,pitcher_outs,pitcher_hits_allowed,pitcher_walks,pitcher_earned_runs",
        "oddsFormat": "american",
        "bookmakers": "draftkings,fanduel" # Kita ambil standar line dari 2 bandar terbesar
    }
    
    print("Menarik data Odds & Lines dari The Odds API...")
    try:
        response = requests.get(url, params=params)
        props_dict = {}
        
        if response.status_code == 200:
            data = response.json()
            for game in data:
                for bookmaker in game.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        market_key = market["key"]
                        for outcome in market.get("outcomes", []):
                            # Nama pitcher ada di deskripsi outcome
                            pitcher = outcome.get("description", "Unknown").lower().strip()
                            
                            if pitcher not in props_dict:
                                props_dict[pitcher] = {}
                            if market_key not in props_dict[pitcher]:
                                props_dict[pitcher][market_key] = {
                                    "line": outcome.get("point", 0), 
                                    "Over": -110, 
                                    "Under": -110
                                }
                            
                            # Memasukkan Odds untuk Over / Under
                            side = outcome.get("name") # "Over" atau "Under"
                            if side in ["Over", "Under"]:
                                props_dict[pitcher][market_key][side] = outcome.get("price")
            print("✅ Sukses menarik data Odds!")
        else:
            print(f"⚠️ The Odds API Error: {response.text}")
            
        return props_dict
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat menarik Odds: {e}")
        return {}

def get_today_schedule():
    """Menarik jadwal dari MLB dan menggabungkannya dengan Odds API."""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher(note)"
    
    print(f"Menarik jadwal MLB untuk tanggal {today}...")
    response = requests.get(url)
    games_list = []
    
    if response.status_code != 200:
        print("❌ Gagal menarik API MLB.")
        return games_list
        
    data = response.json()
    if 'dates' not in data or not data['dates']:
        print("⚠️ Tidak ada jadwal MLB hari ini.")
        return games_list
        
    games = data['dates'][0]['games']
    
    # Eksekusi fungsi penarik Odds
    props_data = get_pitcher_props()
    
    for game in games:
        away_team = game['teams']['away']['team']['name']
        home_team = game['teams']['home']['team']['name']
        
        away_pitcher = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
        home_pitcher = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
        
        # Cocokkan nama pitcher dengan data Odds
        away_props = props_data.get(away_pitcher.lower().strip(), {})
        home_props = props_data.get(home_pitcher.lower().strip(), {})
        
        game_data = {
            "game_id": game['gamePk'],
            "away_team": away_team,
            "home_team": home_team,
            "away_pitcher": away_pitcher,
            "home_pitcher": home_pitcher,
            "away_lineup_rhb_pct": 0.65, 
            "home_lineup_rhb_pct": 0.65,
            "away_pitcher_props": away_props,
            "home_pitcher_props": home_props
        }
        games_list.append(game_data)
        
    return games_list

def save_schedule_to_json(schedule_data, filename="data/today_schedule.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(schedule_data, f, indent=4)
    print(f"✅ BOOM! {len(schedule_data)} pertandingan beserta Odds bandar berhasil disimpan di {filename}")

if __name__ == "__main__":
    schedule = get_today_schedule()
    if schedule:
        save_schedule_to_json(schedule)
