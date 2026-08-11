import requests
import json
import datetime
import os

def get_today_schedule():
    """
    Menarik jadwal pertandingan MLB hari ini dan nama Probable Pitcher 
    langsung dari MLB Stats API resmi.
    """
    # Ambil tanggal hari ini format YYYY-MM-DD
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Endpoint API resmi MLB (gratis & real-time)
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher(note)"
    
    print(f"Menarik jadwal untuk tanggal {today}...")
    response = requests.get(url)
    
    if response.status_code != 200:
        print("❌ Gagal menarik data dari MLB API.")
        return []
        
    data = response.json()
    games_list = []
    
    if 'dates' not in data or not data['dates']:
        print("⚠️ Tidak ada jadwal pertandingan hari ini (Mungkin Off-Day).")
        return games_list
        
    games = data['dates'][0]['games']
    
    for game in games:
        # Cek status game (jangan ambil yang sudah selesai/postponed jika tidak perlu)
        status = game['status']['abstractGameState']
        
        away_team = game['teams']['away']['team']['name']
        home_team = game['teams']['home']['team']['name']
        
        # Ambil Starting Pitcher (TBD jika belum diumumkan)
        away_pitcher = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
        home_pitcher = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
        
        # ATURAN #6: BASE OTOMASI HANDEDNESS
        # Catatan: Lineup resmi biasanya baru rilis 2 jam sebelum main. 
        # Untuk pre-market, kita set standar liga (65% RHB / 35% LHB).
        # Nanti bot ini bisa di-upgrade untuk narik live-lineup mendekati jam main.
        game_data = {
            "game_id": game['gamePk'],
            "status": status,
            "away_team": away_team,
            "home_team": home_team,
            "away_pitcher": away_pitcher,
            "home_pitcher": home_pitcher,
            "away_lineup_rhb_pct": 0.65, 
            "home_lineup_rhb_pct": 0.65
        }
        games_list.append(game_data)
        
    return games_list

def save_schedule_to_json(schedule_data, filename="data/today_schedule.json"):
    """Menyimpan hasil scraping ke format JSON yang siap dibaca oleh Dashboard."""
    # Pastikan folder data/ ada
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(schedule_data, f, indent=4)
    print(f"✅ Sukses! {len(schedule_data)} pertandingan berhasil disimpan di {filename}")

if __name__ == "__main__":
    schedule = get_today_schedule()
    if schedule:
        save_schedule_to_json(schedule)
