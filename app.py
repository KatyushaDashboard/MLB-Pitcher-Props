import streamlit as st
import json
import os
import utils.data_handler as dh
import utils.math_engine as me

st.set_page_config(page_title="MLB Pitcher Props Master", page_icon="⚾", layout="wide")
st.title("⚾ MLB Pitcher Props EV Calculator")
st.markdown("Welcome back, Boss. Mesin +EV siap beraksi.")

# ==========================================
# 1. LOAD DATA & JADWAL
# ==========================================
@st.cache_data
def load_all_data():
    df_master, df_rhb, df_lhb = dh.load_and_clean_data()
    
    schedule_path = 'data/today_schedule.json'
    if os.path.exists(schedule_path):
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)
    else:
        schedule = []
        
    return df_master, df_rhb, df_lhb, schedule

try:
    df_master, df_rhb, df_lhb, schedule = load_all_data()
except Exception as e:
    st.error(f"❌ Error meload data CSV. Pastikan file ada di folder /data/. Detail: {e}")
    st.stop()

if not schedule:
    st.warning("⚠️ File `data/today_schedule.json` belum ada atau kosong. Jalankan workflow Actions 'Manual Bot Updater' di GitHub terlebih dahulu!")
    st.stop()

# ==========================================
# 2. MATCHUP SETUP (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Matchup Setup")

game_options = {f"{g['away_team']} @ {g['home_team']}": g for g in schedule}
selected_game_label = st.sidebar.selectbox("Pilih Pertandingan:", list(game_options.keys()))
selected_game = game_options[selected_game_label]

pitcher_options = {
    f"Away: {selected_game['away_pitcher']} ({selected_game['away_team']})": selected_game['away_pitcher'],
    f"Home: {selected_game['home_pitcher']} ({selected_game['home_team']})": selected_game['home_pitcher']
}
selected_pitcher_label = st.sidebar.selectbox("Pilih Pitcher:", list(pitcher_options.keys()))
selected_pitcher = pitcher_options[selected_pitcher_label]

if selected_pitcher == "TBD" or not selected_pitcher:
    st.warning("⚠️ Starting Pitcher belum diumumkan (TBD). Silakan pilih pertandingan lain.")
    st.stop()

# Handedness Setup
if "Away:" in selected_pitcher_label:
    default_rhb_pct = selected_game.get('home_lineup_rhb_pct', 0.65) * 100
else:
    default_rhb_pct = selected_game.get('away_lineup_rhb_pct', 0.65) * 100

st.sidebar.markdown("---")
st.sidebar.subheader("Opponent Lineup (Handedness)")
pct_rhb = st.sidebar.slider("% Batter Kanan (RHB) di Lineup Lawan", 0.0, 100.0, float(default_rhb_pct), 5.0) / 100.0
pct_lhb = 1.0 - pct_rhb
st.sidebar.write(f"*(Estimasi: {pct_rhb*100:.0f}% RHB, {pct_lhb*100:.0f}% LHB)*")

# PENYESUAIAN JULI-AGUSTUS: Default PA diturunkan ke 19.5 (Dog Days / Innings Limit)
expected_pa = st.sidebar.number_input(
    "Expected Batters Faced (PA)", 
    min_value=10.0, 
    max_value=35.0, 
    value=20.0, 
    step=0.5,
    help="Diturunkan ke 20 PA untuk mengantisipasi kelelahan Juli-Agustus & penarikan pitcher lebih awal."
)

# ==========================================
# 3. STAT LOOKUP & LOGIC (BACKEND)
# ==========================================
stats = dh.get_pitcher_stats(selected_pitcher, df_master, df_rhb, df_lhb)

if not stats:
    st.error(f"❌ Pitcher '{selected_pitcher}' tidak ditemukan di database. Pastikan nama sesuai.")
    st.stop()

if not stats['vs_rhb'] and not stats['vs_lhb']:
    st.warning(f"⚠️ Data L60 tidak ditemukan untuk {selected_pitcher}. Menggunakan data Master Full Season.")
    stat_rhb = stats['master']
    stat_lhb = stats['master']
else:
    stat_rhb = stats['vs_rhb'] if stats['vs_rhb'] else stats['vs_lhb']
    stat_lhb = stats['vs_lhb'] if stats['vs_lhb'] else stats['vs_rhb']

# Pembobotan Stat berdasarkan Lineup Lawan (Hyper-Recent L60)
weighted_k_pct = (float(stat_rhb['k_percent']) * pct_rhb) + (float(stat_lhb['k_percent']) * pct_lhb)
weighted_bb_pct = (float(stat_rhb['bb_percent']) * pct_rhb) + (float(stat_lhb['bb_percent']) * pct_lhb)
weighted_xba = (float(stat_rhb['xba']) * pct_rhb) + (float(stat_lhb['xba']) * pct_lhb)
weighted_xwoba = (float(stat_rhb['xwoba']) * pct_rhb) + (float(stat_lhb['xwoba']) * pct_lhb)

# Hitung nilai ekspektasi untuk semua pasar prop
x_strikeouts = me.calculate_xk(expected_pa, weighted_k_pct)
x_outs = me.calculate_xouts(expected_pa, weighted_bb_pct, weighted_xba)
x_hits = me.calculate_xhits(expected_pa, weighted_bb_pct, weighted_xba)
x_walks = me.calculate_xbb(expected_pa, weighted_bb_pct)
x_er = me.calculate_xer(x_outs, weighted_xwoba)

## ==========================================
# 4. DASHBOARD & KALKULATOR +EV (UI MAIN)
# ==========================================
st.subheader(f"📊 Proyeksi Model Lengkap untuk {selected_pitcher.title()}")

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
m_col1.metric("Expected K's", f"{x_strikeouts:.2f}", f"K%: {weighted_k_pct:.1f}%")
m_col2.metric("Expected Outs", f"{x_outs:.1f}", "-7.5% Fatigue")
m_col3.metric("Expected Hits", f"{x_hits:.2f}", f"xBA: {weighted_xba:.3f}")
m_col4.metric("Expected Walks", f"{x_walks:.2f}", f"BB%: {weighted_bb_pct:.1f}%")
m_col5.metric("Expected ER", f"{x_er:.2f}", f"xwOBA: {weighted_xwoba:.3f}")

st.markdown("---")
st.subheader("💰 Sportsbook Odds & +EV Analysis")

# Pilihan 5 Pasar Prop Utama
prop_type = st.radio(
    "Pilih Prop Market:", 
    ["Strikeouts", "Pitching Outs", "Hits Allowed", "Walks Allowed", "Earned Runs"], 
    horizontal=True
)

# API Market Key Mapping
market_keys_map = {
    "Strikeouts": "pitcher_strikeouts",
    "Pitching Outs": "pitcher_outs",
    "Hits Allowed": "pitcher_hits_allowed",
    "Walks Allowed": "pitcher_walks",
    "Earned Runs": "pitcher_earned_runs"
}

# Mapping proyeksi & Fallback Default Line jika bandar belum merilis line
prop_map = {
    "Strikeouts": (x_strikeouts, 4.5),
    "Pitching Outs": (x_outs, 15.5),
    "Hits Allowed": (x_hits, 4.5),
    "Walks Allowed": (x_walks, 1.5),
    "Earned Runs": (x_er, 2.5)
}

current_xval, fallback_line = prop_map[prop_type]

# Tarik data API Odds dari JSON
if "Away:" in selected_pitcher_label:
    pitcher_props_api = selected_game.get('away_pitcher_props', {})
else:
    pitcher_props_api = selected_game.get('home_pitcher_props', {})

api_market_key = market_keys_map[prop_type]
api_prop_data = pitcher_props_api.get(api_market_key, {})

# Tentukan Line (Pakai Line API jika ada, jika tidak pakai fallback)
api_line = api_prop_data.get("line")
default_line_val = float(api_line) if api_line is not None else float(fallback_line)

# UI Input
col_in1, col_in2, col_in3 = st.columns(3)
with col_in1:
    line_input = st.number_input("O/U Line Bandar", value=default_line_val, step=0.5, 
                                 help="Otomatis diambil dari Odds API jika tersedia.")
with col_in2:
    bet_side = st.selectbox("Posisi Bet:", ["Over", "Under"])
    
with col_in3:
    # Set Odds otomatis berdasarkan pilihan bet_side (Over/Under)
    api_odds = api_prop_data.get(bet_side)
    default_odds_val = int(api_odds) if api_odds is not None else -110
    odds_input = st.number_input("American Odds (-110, +120, dll)", value=default_odds_val, step=5,
                                 help="Otomatis diambil dari Odds API jika tersedia.")

# Poisson Math
model_prob = me.get_poisson_probability(current_xval, line_input, bet_side)
implied_prob = me.get_implied_probability(odds_input)
edge = model_prob - implied_prob

# Output Hasil +EV / -EV
st.markdown("### Hasil Analisis EV")
res_c1, res_c2, res_c3 = st.columns(3)
res_c1.metric("Implied Prob (Bandar)", f"{implied_prob:.1f}%")
res_c2.metric("Model Prob (Kita)", f"{model_prob:.1f}%")

with res_c3:
    if edge > 0:
        st.success(f"🔥 +EV DETECTED! Edge: +{edge:.1f}%")
        st.write(f"**Saran: SIKAT {bet_side.upper()} {line_input}!**")
    else:
        st.error(f"⚠️ -EV (BAD BET). Edge: {edge:.1f}%")
        st.write("**Saran: SKIP / PASS**")
