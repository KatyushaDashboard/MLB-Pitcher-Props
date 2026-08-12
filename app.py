import streamlit as st
import json
import os
import utils.data_handler as dh
import utils.math_engine as me

st.set_page_config(page_title="MLB Pitcher Props Master", page_icon="⚾", layout="wide")
st.title("⚾ MLB Pitcher Props EV Calculator")
st.markdown("Welcome back, Boss. Mesin +EV 100% Otomatis & SGP Recommender siap beraksi.")

# ==========================================
# 1. LOAD DATA & JADWAL
# ==========================================
@st.cache_data
def load_all_data():
    df_master, df_rhb, df_lhb = dh.load_and_clean_data()
    schedule_path = 'data/today_schedule.json'
    schedule = json.load(open(schedule_path, 'r')) if os.path.exists(schedule_path) else []
    return df_master, df_rhb, df_lhb, schedule

try:
    df_master, df_rhb, df_lhb, schedule = load_all_data()
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

if not schedule:
    st.warning("⚠️ File `data/today_schedule.json` belum ada. Jalankan Actions 'Manual Bot Updater' di GitHub!")
    st.stop()

# ==========================================
# 2. MATCHUP SETUP (SIDEBAR OTOMATIS)
# ==========================================
st.sidebar.header("⚙️ Matchup Selection")

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
    st.warning("⚠️ Starting Pitcher belum diumumkan (TBD).")
    st.stop()

# PENARIKAN PARAMETER OTOMATIS
if "Away:" in selected_pitcher_label:
    pct_rhb = selected_game.get('home_lineup_rhb_pct', 0.65)
    expected_pa = selected_game.get('away_pitcher_pa', 19.5)
else:
    pct_rhb = selected_game.get('away_lineup_rhb_pct', 0.65)
    expected_pa = selected_game.get('home_pitcher_pa', 19.5)

pct_lhb = 1.0 - pct_rhb

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Auto-Injected Matchup Parameters")
st.sidebar.info(f"**Lineup Lawan:** {pct_rhb*100:.0f}% RHB / {pct_lhb*100:.0f}% LHB\n*(Dihitung otomatis dari Projected Starters / Active Roster)*")
st.sidebar.success(f"**Expected PA:** {expected_pa} Batters Faced\n*(Dihitung otomatis dari Rata-Rata PA/GS 30 Hari Terakhir)*")

# Opsi manual override
with st.sidebar.expander("🛠️ Manual Override (Opsional)"):
    pct_rhb = st.slider("Override % RHB", 0.0, 100.0, float(pct_rhb*100), 5.0) / 100.0
    pct_lhb = 1.0 - pct_rhb
    expected_pa = st.number_input("Override Expected PA", min_value=10.0, max_value=35.0, value=float(expected_pa), step=0.5)

# ==========================================
# 3. STAT LOOKUP & LOGIC (BACKEND)
# ==========================================
stats = dh.get_pitcher_stats(selected_pitcher, df_master, df_rhb, df_lhb)

if not stats:
    st.error(f"❌ Pitcher '{selected_pitcher}' tidak ditemukan di database CSV.")
    st.stop()

if not stats['vs_rhb'] and not stats['vs_lhb']:
    st.warning(f"⚠️ Data L60 tidak ditemukan untuk {selected_pitcher}. Menggunakan data Full Season.")
    stat_rhb = stats['master']
    stat_lhb = stats['master']
else:
    stat_rhb = stats['vs_rhb'] if stats['vs_rhb'] else stats['vs_lhb']
    stat_lhb = stats['vs_lhb'] if stats['vs_lhb'] else stats['vs_rhb']

weighted_k_pct = (float(stat_rhb['k_percent']) * pct_rhb) + (float(stat_lhb['k_percent']) * pct_lhb)
weighted_bb_pct = (float(stat_rhb['bb_percent']) * pct_rhb) + (float(stat_lhb['bb_percent']) * pct_lhb)
weighted_xba = (float(stat_rhb['xba']) * pct_rhb) + (float(stat_lhb['xba']) * pct_lhb)
weighted_xwoba = (float(stat_rhb['xwoba']) * pct_rhb) + (float(stat_lhb['xwoba']) * pct_lhb)

x_strikeouts = me.calculate_xk(expected_pa, weighted_k_pct)
x_outs = me.calculate_xouts(expected_pa, weighted_bb_pct, weighted_xba)
x_hits = me.calculate_xhits(expected_pa, weighted_bb_pct, weighted_xba)
x_walks = me.calculate_xbb(expected_pa, weighted_bb_pct)
x_er = me.calculate_xer(x_outs, weighted_xwoba)

# ==========================================
# 4. DASHBOARD PROYEKSI MODEL
# ==========================================
st.subheader(f"📊 Proyeksi Model Lengkap untuk {selected_pitcher.title()}")

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
m_col1.metric("Expected K's", f"{x_strikeouts:.2f}", f"K%: {weighted_k_pct:.1f}%")
m_col2.metric("Expected Outs", f"{x_outs:.1f}", "-7.5% Fatigue")
m_col3.metric("Expected Hits", f"{x_hits:.2f}", f"xBA: {weighted_xba:.3f}")
m_col4.metric("Expected Walks", f"{x_walks:.2f}", f"BB%: {weighted_bb_pct:.1f}%")
m_col5.metric("Expected ER", f"{x_er:.2f}", f"xwOBA: {weighted_xwoba:.3f}")

st.markdown("---")

## ==========================================
# 5. 🎯 🤖 AUTOMATED SGP RECOMMENDER (1 MATCHUP / 2 PITCHERS)
# ==========================================
st.subheader(f"🎯 🤖 SGP AI Recommender — {selected_game['away_team']} @ {selected_game['home_team']}")
st.markdown("Memindai **10 pasar prop dari KEDUA Starting Pitcher** dalam pertandingan ini untuk mencari leg **Same Game Parlay (SGP)** dengan **Model Prob >= 55%** & **Edge Positif (+EV)**.")

pitchers_data = []

# 1. Away Pitcher
away_p_name = selected_game['away_pitcher']
if away_p_name and away_p_name != "TBD":
    away_stats = dh.get_pitcher_stats(away_p_name, df_master, df_rhb, df_lhb)
    if away_stats:
        a_rhb = away_stats['vs_rhb'] if away_stats['vs_rhb'] else away_stats['master']
        a_lhb = away_stats['vs_lhb'] if away_stats['vs_lhb'] else away_stats['master']
        a_pct_rhb = selected_game.get('home_lineup_rhb_pct', 0.65)
        a_pct_lhb = 1.0 - a_pct_rhb
        a_pa = selected_game.get('away_pitcher_pa', 19.5)
        
        a_wk = (float(a_rhb['k_percent']) * a_pct_rhb) + (float(a_lhb['k_percent']) * a_pct_lhb)
        a_wbb = (float(a_rhb['bb_percent']) * a_pct_rhb) + (float(a_lhb['bb_percent']) * a_pct_lhb)
        a_xba = (float(a_rhb['xba']) * a_pct_rhb) + (float(a_lhb['xba']) * a_pct_lhb)
        a_xwoba = (float(a_rhb['xwoba']) * a_pct_rhb) + (float(a_lhb['xwoba']) * a_pct_lhb)
        
        pitchers_data.append({
            "name": away_p_name,
            "team": selected_game['away_team'],
            "role": "Away",
            "props_api": selected_game.get('away_pitcher_props', {}),
            "projections": {
                "Strikeouts": (me.calculate_xk(a_pa, a_wk), "pitcher_strikeouts", 4.5),
                "Pitching Outs": (me.calculate_xouts(a_pa, a_wbb, a_xba), "pitcher_outs", 15.5),
                "Hits Allowed": (me.calculate_xhits(a_pa, a_wbb, a_xba), "pitcher_hits_allowed", 4.5),
                "Walks Allowed": (me.calculate_xbb(a_pa, a_wbb), "pitcher_walks", 1.5),
                "Earned Runs": (me.calculate_xer(me.calculate_xouts(a_pa, a_wbb, a_xba), a_xwoba), "pitcher_earned_runs", 2.5)
            }
        })

# 2. Home Pitcher
home_p_name = selected_game['home_pitcher']
if home_p_name and home_p_name != "TBD":
    home_stats = dh.get_pitcher_stats(home_p_name, df_master, df_rhb, df_lhb)
    if home_stats:
        h_rhb = home_stats['vs_rhb'] if home_stats['vs_rhb'] else home_stats['master']
        h_lhb = home_stats['vs_lhb'] if home_stats['vs_lhb'] else home_stats['master']
        h_pct_rhb = selected_game.get('away_lineup_rhb_pct', 0.65)
        h_pct_lhb = 1.0 - h_pct_rhb
        h_pa = selected_game.get('home_pitcher_pa', 19.5)
        
        h_wk = (float(h_rhb['k_percent']) * h_pct_rhb) + (float(h_lhb['k_percent']) * h_pct_lhb)
        h_wbb = (float(h_rhb['bb_percent']) * h_pct_rhb) + (float(h_lhb['bb_percent']) * h_pct_lhb)
        h_xba = (float(h_rhb['xba']) * h_pct_rhb) + (float(h_lhb['xba']) * h_pct_lhb)
        h_xwoba = (float(h_rhb['xwoba']) * h_pct_rhb) + (float(h_lhb['xwoba']) * h_pct_lhb)
        
        pitchers_data.append({
            "name": home_p_name,
            "team": selected_game['home_team'],
            "role": "Home",
            "props_api": selected_game.get('home_pitcher_props', {}),
            "projections": {
                "Strikeouts": (me.calculate_xk(h_pa, h_wk), "pitcher_strikeouts", 4.5),
                "Pitching Outs": (me.calculate_xouts(h_pa, h_wbb, h_xba), "pitcher_outs", 15.5),
                "Hits Allowed": (me.calculate_xhits(h_pa, h_wbb, h_xba), "pitcher_hits_allowed", 4.5),
                "Walks Allowed": (me.calculate_xbb(h_pa, h_wbb), "pitcher_walks", 1.5),
                "Earned Runs": (me.calculate_xer(me.calculate_xouts(h_pa, h_wbb, h_xba), h_xwoba), "pitcher_earned_runs", 2.5)
            }
        })

matchup_sgp_legs = []

for p in pitchers_data:
    p_name = p['name']
    p_team = p['team']
    props_api = p['props_api']
    
    for prop_label, (exp_val, api_key, fallback_line) in p['projections'].items():
        api_data = props_api.get(api_key, {})
        line = float(api_data.get("line")) if api_data.get("line") is not None else float(fallback_line)
        
        for side in ["Over", "Under"]:
            odds = int(api_data.get(side)) if api_data.get(side) is not None else -110
            model_p = me.get_poisson_probability(exp_val, line, side)
            implied_p = me.get_implied_probability(odds)
            edge = model_p - implied_p
            
            if model_p >= 55.0 and edge > 0:
                matchup_sgp_legs.append({
                    "pitcher": p_name,
                    "team": p_team,
                    "prop": prop_label,
                    "side": side,
                    "line": line,
                    "exp_val": exp_val,
                    "model_prob": model_p,
                    "implied_prob": implied_p,
                    "odds": odds,
                    "edge": edge
                })

if matchup_sgp_legs:
    st.success(f"🔥 Ditemukan **{len(matchup_sgp_legs)} Leg +EV** dari KEDUA Pitcher di match ini (Model Prob >= 55% & Edge > 0%):")
    
    cols = st.columns(min(len(matchup_sgp_legs), 3))
    for idx, leg in enumerate(matchup_sgp_legs):
        col_target = cols[idx % len(cols)]
        with col_target:
            odds_str = f"+{leg['odds']}" if leg['odds'] > 0 else f"{leg['odds']}"
            st.markdown(f"""
            <div style="border:2px solid #28a745; border-radius:10px; padding:15px; margin-bottom:12px; background-color:#1e2b20;">
                <span style="background-color:#2e7d32; color:white; padding:2px 8px; border-radius:4px; font-size:12px;"><b>{leg['pitcher'].title()} ({leg['team']})</b></span>
                <h4 style="margin:8px 0 4px 0; color:#4caf50;">⚾ {leg['side']} {leg['line']} {leg['prop']}</h4>
                <p style="margin:4px 0; font-size:14px;"><b>Odds Bandar:</b> {odds_str} (Implied: {leg['implied_prob']:.1f}%)</p>
                <p style="margin:4px 0; font-size:14px;"><b>Model Prob:</b> {leg['model_prob']:.1f}%</p>
                <p style="margin:4px 0; font-size:14px; color:#81c784;"><b>Edge (+EV):</b> +{leg['edge']:.1f}%</p>
                <small style="color:#aaa;">Expected: {leg['exp_val']:.2f}</small>
            </div>
            """, unsafe_allow_html=True)
            
    st.info("💡 **SGP Tip:** Gabungkan 2-3 leg dari kartu di atas (bisa campur Away & Home Pitcher) menjadi 1 tiket Same Game Parlay di sportsbook Anda!")
else:
    st.warning("⚠️ Tidak ada Leg SGP +EV yang memenuhi syarat dari kedua Pitcher dalam pertandingan ini.")

st.markdown("---")

# ==========================================
# 6. MANUAL PROP CALCULATOR (SINGLES)
# ==========================================
st.subheader("💰 Single Prop Inspector")
st.markdown(f"*(Memeriksa Line untuk pitcher yang dipilih di sidebar: **{selected_pitcher.title()}**)*")

prop_type = st.radio("Pilih Prop Market untuk Cek Detail:", ["Strikeouts", "Pitching Outs", "Hits Allowed", "Walks Allowed", "Earned Runs"], horizontal=True)

market_keys_map = {
    "Strikeouts": "pitcher_strikeouts",
    "Pitching Outs": "pitcher_outs",
    "Hits Allowed": "pitcher_hits_allowed",
    "Walks Allowed": "pitcher_walks",
    "Earned Runs": "pitcher_earned_runs"
}

prop_map = {
    "Strikeouts": (x_strikeouts, 4.5),
    "Pitching Outs": (x_outs, 15.5),
    "Hits Allowed": (x_hits, 4.5),
    "Walks Allowed": (x_walks, 1.5),
    "Earned Runs": (x_er, 2.5)
}

current_xval, fallback_line = prop_map[prop_type]

pitcher_props_api = selected_game.get('away_pitcher_props', {}) if "Away:" in selected_pitcher_label else selected_game.get('home_pitcher_props', {})
api_market_key = market_keys_map[prop_type]
api_prop_data = pitcher_props_api.get(api_market_key, {})

api_line = api_prop_data.get("line")
default_line_val = float(api_line) if api_line is not None else float(fallback_line)

col_in1, col_in2, col_in3 = st.columns(3)
with col_in1:
    line_input = st.number_input("O/U Line Bandar", value=default_line_val, step=0.5)
with col_in2:
    bet_side = st.selectbox("Posisi Bet:", ["Over", "Under"])
with col_in3:
    api_odds = api_prop_data.get(bet_side)
    default_odds_val = int(api_odds) if api_odds is not None else -110
    odds_input = st.number_input("American Odds (-110, +120, dll)", value=default_odds_val, step=5)

model_prob = me.get_poisson_probability(current_xval, line_input, bet_side)
implied_prob = me.get_implied_probability(odds_input)
edge = model_prob - implied_prob

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
