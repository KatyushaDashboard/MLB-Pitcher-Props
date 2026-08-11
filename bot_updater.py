import requests
import json
import datetime
import os

ODDS_API_KEY = "c8d93d667bf40310980a6d68e154c96f"

def get_pitcher_props():
    """
    Menarik Prop Lines & Odds dari The Odds API.
    Aturan API: Player Props harus ditarik menggunakan Event ID spesifik per pertandingan.
    """
    base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb"
    props_dict = {}
    
    print("Mendapatkan daftar Pertandingan (Event) dari The Odds API...")
    
    # LANGKAH 1: Dapatkan daftar ID event/pertandingan hari ini
    events_response = requests.get(f"{base_url}/events", params={"apiKey": ODDS_API_KEY})
    
    if events_response.status_code != 200:
        print(f"❌ Gagal menarik events: {events_response.text}")
        return props_dict
        
    events = events_response.json()
    if not events:
        print("⚠️ Tidak ada event MLB yang ditemukan di The Odds API hari ini.")
        return props_dict

    print(f"✅ Ditemukan {len(events)} pertandingan. Menarik Line Prop untuk masing-masing pitcher...")
    
    # LANGKAH 2: Loop per event untuk menarik Player Props
    markets_needed = "pitcher_strikeouts,pitcher_outs,pitcher_hits_allowed,pitcher_walks,pitcher_earned_runs"
    
    for event in events:
        event_id = event['id']
        odds_url = f"{base_url}/events/{event_id}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": markets_needed,
            "oddsFormat": "american",
            "bookmakers": "draftkings,fanduel" # Tarik data dari bandar utama
        }
        
        try:
            odds_response = requests.get(odds_url, params=params)
            
            if odds_response.status_code == 200:
                event_data = odds_response.json()
                
                # Ekstrak data dan masukkan ke dictionary
                for bookmaker in event_data.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        market_key = market["key"]
                        for outcome in market.get("outcomes", []):
                            pitcher_name = outcome.get("description", "Unknown").lower().strip()
                            side = outcome.get("name") # "Over" atau "Under"
                            
                            if pitcher_name not in props_dict:
                                props_dict[pitcher_name] = {}
                            if market_key not in props_dict[pitcher_name]:
                                props_dict[pitcher_name][market_key] = {
                                    "line": outcome.get("point", 0),
                                    "Over": -110,
                                    "Under": -110
                                }
                            
                            # Memasukkan nilai American Odds
                            if side in ["Over", "Under"]:
                                props_dict[pitcher_name][market_key][side] = outcome.get("price")
            else:
                pass # Abaikan jika bandar belum merilis prop line untuk event ini
                
        except Exception as e:
            print(f"❌ Error saat menarik data untuk event {event_id}: {e}")
            
    print(f"✅ Sukses memetakan Odds untuk {len(props_dict)} pitcher!")
    return props_dict

def get_today_schedule():
    """Menarik jadwal dari MLB dan menggabungkannya dengan Odds dari Sportsbook."""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher(note)"
    
    print(f"Menarik jadwal pertandingan resmi MLB untuk tanggal {today}...")
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
        
        # Cocokkan nama pitcher MLB dengan nama dari Odds API
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
    print(f"🔥 BOOM! {len(schedule_data)} pertandingan beserta Odds bandar berhasil disimpan ke {filename}")

if __name__ == "__main__":
    schedule = get_today_schedule()
    if schedule:
        save_schedule_to_json(schedule)
