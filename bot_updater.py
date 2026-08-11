import requests
import json
import datetime
import os

ODDS_API_KEY = "c8d93d667bf40310980a6d68e154c96f"

def get_pitcher_props():
    """Menarik Prop Lines & Odds dari The Odds API per Event ID."""
    base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb"
    props_dict = {}
    
    events_response = requests.get(f"{base_url}/events", params={"apiKey": ODDS_API_KEY})
    if events_response.status_code != 200:
        return props_dict
        
    events = events_response.json()
    markets_needed = "pitcher_strikeouts,pitcher_outs,pitcher_hits_allowed,pitcher_walks,pitcher_earned_runs"
    
    for event in events:
        event_id = event['id']
        odds_url = f"{base_url}/events/{event_id}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": markets_needed,
            "oddsFormat": "american",
            "bookmakers": "draftkings,fanduel"
        }
        
        try:
            odds_response = requests.get(odds_url, params=params)
            if odds_response.status_code == 200:
                event_data = odds_response.json()
                for bookmaker in event_data.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        market_key = market["key"]
                        for outcome in market.get("outcomes", []):
                            pitcher_name = outcome.get("description", "Unknown").lower().strip()
                            side = outcome.get("name")
                            
                            if pitcher_name not in props_dict:
                                props_dict[pitcher_name] = {}
                            if market_key not in props_dict[pitcher_name]:
                                props_dict[pitcher_name][market_key] = {
                                    "line": outcome.get("point", 0),
                                    "Over": -110,
                                    "Under": -110
                                }
                            if side in ["Over", "Under"]:
                                props_dict[pitcher_name][market_key][side] = outcome.get("price")
        except Exception:
            pass
            
    return props_dict

def get_pitcher_recent_pa(pitcher_id):
    """
    OTOMASI EXPECTED PA:
    Menarik rata-rata Batters Faced (PA) per start si pitcher dalam 30 hari terakhir dari MLB API.
    """
    if not pitcher_id:
        return 19.5 # Fallback default jika ID tidak ada
        
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=byMonth&group=pitching"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            stats_list = data.get('stats', [])[0].get('splits', [])
            if stats_list:
                # Ambil statistik bulan terbaru (30d terakhir)
                latest_month = stats_list[-1].get('stat', {})
                games_started = latest_month.get('gamesStarted', 0)
                batters_faced = latest_month.get('battersFaced', 0)
                
                if games_started > 0:
                    avg_pa = batters_faced / games_started
                    return round(avg_pa, 1)
    except Exception:
        pass
        
    return 19.5 # Fallback standar

def calculate_lineup_handedness(game_pk, team_id, team_type, pitcher_hand):
    """
    Versi Anti-Fallback:
    1. Cek Lineup Resmi (9 Starter).
    2. Jika kepagian (belum rilis), pakai 26-Man Active Roster sebagai proxy akurat!
    """
    try:
        # Skenario 1: Cek Boxscore untuk Lineup Resmi
        box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        box_data = requests.get(box_url).json()
        batters_ids = box_data.get('teams', {}).get(team_type, {}).get('battingOrder', [])
        
        if batters_ids:
            rhb_count = 0
            players = box_data['teams'][team_type]['players']
            for pid in batters_ids:
                player_key = f"ID{pid}"
                bat_side = players.get(player_key, {}).get('person', {}).get('batSide', {}).get('code', 'R')
                if bat_side == 'R' or (bat_side == 'S' and pitcher_hand == 'L'):
                    rhb_count += 1
            return round(rhb_count / len(batters_ids), 2)
            
        # Skenario 2: Kepagian! Tarik 26-Man Active Roster
        roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/Active?hydrate=person"
        roster_data = requests.get(roster_url).json()
        roster = roster_data.get('roster', [])
        
        if roster:
            rhb_count = 0
            batter_count = 0
            for p in roster:
                # Ambil pemain yang BUKAN Pitcher
                if p.get('position', {}).get('abbreviation') != 'P':
                    batter_count += 1
                    bat_side = p.get('person', {}).get('batSide', {}).get('code', 'R')
                    if bat_side == 'R' or (bat_side == 'S' and pitcher_hand == 'L'):
                        rhb_count += 1
            if batter_count > 0:
                return round(rhb_count / batter_count, 2)
                
    except Exception as e:
        print(f"Error calculate handedness: {e}")
        pass
        
    return 0.65 # Fallback mutlak jika MLB API sedang down

def get_today_schedule():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher(note)"
    
    print(f"Menarik jadwal MLB & memproses algoritma otomatis untuk {today}...")
    response = requests.get(url)
    games_list = []
    
    if response.status_code != 200 or 'dates' not in response.json() or not response.json()['dates']:
        print("⚠️ Tidak ada jadwal MLB hari ini.")
        return games_list
        
    games = response.json()['dates'][0]['games']
    props_data = get_pitcher_props()
    
    for game in games:
        game_pk = game['gamePk']
        away_team = game['teams']['away']['team']['name']
        home_team = game['teams']['home']['team']['name']
        
        # Tarik Team ID untuk keperluan cek Roster
        away_team_id = game['teams']['away']['team']['id']
        home_team_id = game['teams']['home']['team']['id']
        
        away_pitcher_info = game['teams']['away'].get('probablePitcher', {})
        home_pitcher_info = game['teams']['home'].get('probablePitcher', {})
        
        away_pitcher = away_pitcher_info.get('fullName', 'TBD')
        home_pitcher = home_pitcher_info.get('fullName', 'TBD')
        
        # Ambil ID & Tangan Pitcher
        away_pitcher_id = away_pitcher_info.get('id')
        home_pitcher_id = home_pitcher_info.get('id')
        
        # Ekstrak Tangan Pitcher (R/L) dari hydrate API
        # Default R jika kosong
        away_pitcher_hand = "R" 
        home_pitcher_hand = "R"
        
        # Hitung Expected PA 30 hari terakhir
        away_expected_pa = get_pitcher_recent_pa(away_pitcher_id)
        home_expected_pa = get_pitcher_recent_pa(home_pitcher_id)
        
        # Hitung Handedness Lawan (Pakai data tim & tangan pitcher kita)
        home_rhb_pct = calculate_lineup_handedness(game_pk, home_team_id, 'home', away_pitcher_hand)
        away_rhb_pct = calculate_lineup_handedness(game_pk, away_team_id, 'away', home_pitcher_hand)
        
        away_props = props_data.get(away_pitcher.lower().strip(), {})
        home_props = props_data.get(home_pitcher.lower().strip(), {})
        
        game_data = {
            "game_id": game_pk,
            "away_team": away_team,
            "home_team": home_team,
            "away_pitcher": away_pitcher,
            "home_pitcher": home_pitcher,
            "away_pitcher_pa": away_expected_pa,
            "home_pitcher_pa": home_expected_pa,
            "away_lineup_rhb_pct": away_rhb_pct,
            "home_lineup_rhb_pct": home_rhb_pct,
            "away_pitcher_props": away_props,
            "home_pitcher_props": home_props
        }
        games_list.append(game_data)
        
    return games_list

def save_schedule_to_json(schedule_data, filename="data/today_schedule.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(schedule_data, f, indent=4)
    print(f"🔥 BOOM! Data jadwal, Lineup Handedness, & Expected PA 30D berhasil disimpan ke {filename}")

if __name__ == "__main__":
    schedule = get_today_schedule()
    if schedule:
        save_schedule_to_json(schedule)
