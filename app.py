import streamlit as st
import json
import os
import pandas as pd
from utils.data_handler import load_and_clean_data, get_pitcher_stats
import utils.math_engine as me

# Set UI Streamlit
st.set_page_config(
    page_title="MLB Pitcher Props Master",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ MLB Pitcher Props EV Calculator")
st.markdown("Welcome back, Boss. Mesin +EV siap beraksi.")

# ==========================================
# 1. LOAD DATA & JADWAL
# ==========================================
@st.cache_data
def load_all_data():
    df_master, df_rhb, df_lhb = load_and_clean_data()
    
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

# Format dropdown pilihan game
game_options = {f"{g['away_team']} @ {g['home_team']}": g for g in schedule}
selected_game_label = st.sidebar.selectbox("Pilih Pertandingan:", list(game_options.keys()))
selected_game = game_options[selected_game_label]

# Dropdown pilihan Starting Pitcher dari game tersebut
pitcher_options = {
    f"Away: {selected_game['away_pitcher']} ({selected_game['away_team']})": selected_game['away_pitcher'],
    f"Home: {selected_game['home_pitcher']} ({selected_game['home_team']})": selected_game['home_pitcher']
}
selected_pitcher_label = st.sidebar.selectbox("Pilih Pitcher:", list(pitcher_options.keys()))
selected_pitcher = pitcher_options[selected_pitcher_label]

if selected_pitcher == "TBD" or not selected_pitcher:
    st.warning("⚠️ Starting Pitcher belum diumumkan (TBD). Silakan pilih pertandingan lain.")
    st.stop()

# Set Handedness Otomatis (Aturan #6)
if "Away:" in selected_pitcher_label:
    default_rhb_pct = selected_game.get('home_lineup_rhb_pct', 0.65) * 100
else:
    default_rhb_pct = selected_game.get('away_lineup_rhb_pct', 0.65) * 100

st.sidebar.markdown("---")
st.sidebar.subheader("Opponent Lineup (Handedness)")
pct_rhb = st.sidebar.slider("% Batter Kanan (RHB) di Lineup Lawan", 0.0, 100.0, float(default_rhb_pct), 5.0) / 100
pct_lhb = 1.0 - pct_rhb
st.sidebar.write(f"*(Estimasi: {pct_rhb*100:.0f}% RHB, {pct_lhb*100:.0f}% LHB)*")

# Batters Faced (PA) Input
expected_pa = st.sidebar.number_input("Expected Batters Faced (PA)", min_value=10.0, max_value=35.0, value=22.5, step=0.5)

# ==========================================
# 3. STAT LOOKUP & LOGIC (BACKEND)
# ==========================================
# ATURAN #1: Matching string aman via data_handler
stats = get_pitcher_stats(selected_pitcher, df_master, df_rhb, df_lhb)

if not stats:
    st.error(f"❌ Pitcher '{selected_pitcher}' tidak ditemukan di database CSV (`master_pitcher2026.csv`). Pastikan nama sesuai.")
    st.stop()

if not stats['vs_rhb'] and not stats['vs_lhb']:
    st.warning(f"⚠️ Data splits L60 tidak ditemukan untuk {selected_pitcher}.")
    st.stop()

# Fallback jika hanya ada data salah satu handedness
stat_rhb = stats['vs_rhb'] if stats['vs_rhb'] else stats['vs_lhb']
stat_lhb = stats['vs_lhb'] if stats['vs_lhb'] else stats['vs_rhb']

# ATURAN #2: Mode Hyper-Recent (Pembobotan L60 berdasarkan lineup lawan)
weighted_k_pct = (stat_rhb['k_percent'] * pct_rhb) + (stat_lhb['k_percent'] * pct_lhb)
weighted_bb_pct = (stat_rhb['bb_percent'] * pct_rhb) + (stat_lhb['bb_percent'] * pct_lhb)
weighted_xba = (stat_rhb['xba'] * pct_rhb) + (stat_lhb['xba'] * pct_lhb)

# Hitung nilai ekspektasi
x_strikeouts = me.calculate_xk(expected_pa, weighted_k_pct)
# ATURAN #3: Fatigue Penalty sudah otomatis terhitung di calculate_xouts
x_outs = me.calculate_xouts(expected_pa, weighted_bb_pct, weighted_xba)

# ==========================================
# 4. DASHBOARD & KALKULATOR +EV (UI MAIN)
# ==========================================
st.subheader(f"📊 Proyeksi Model untuk {selected_pitcher.title()}")

col_m1, col_m2 = st.columns(2)
with col_m1:
    st.metric(
        label="Expected Strikeouts (xK)",
        value=f"{x_strikeouts:.2f}",
        delta=f"Weighted K%: {weighted_k_pct:.1f}%"
    )
with col_m2:
    st.metric(
        label="Expected Outs (xOuts)",
        value=f"{x_outs:.2f}",
        delta="Includes 7.5% Fatigue Penalty",
        delta_color="off"
    )

st.markdown("---")
st.subheader("💰 Sportsbook Odds & +EV Analysis")

prop_type = st.radio("Pilih Prop Market:", ["Strikeouts", "Pitching Outs"], horizontal=True)

col_in1, col_in2, col_in3 = st.columns(3)
with col_in1:
    line_input = st.number_input("O/U Line Bandar", value=5.5 if prop_type=="Strikeouts" else 15.5, step=0.5)
with col_in2:
    bet_side = st.selectbox("Posisi Bet:", ["Over", "Under"])
with col_in3:
    odds_input = st.number_input("American Odds (-110, +120, dll)", value=-110, step=5)

# ATURAN #4: Poisson Math
if prop_type == "Strikeouts":
    model_prob = me.get_poisson_probability(x_strikeouts, line_input, bet_side)
else:
    model_prob = me.get_poisson_probability(x_outs, line_input, bet_side)

implied_prob = me.get_implied_probability(odds_input)
edge = model_prob - implied_prob

# ATURAN #5: Output Margin +EV / -EV
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
