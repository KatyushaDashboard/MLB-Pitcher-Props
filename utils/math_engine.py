from scipy.stats import poisson

def calculate_xouts(pa_per_game, bb_percent, xba):
    """
    Menghitung Expected Outs murni berdasarkan kemampuan pitcher membatasi hit/walk.
    """
    # 1. Konversi persen ke desimal
    bb_rate = bb_percent / 100
    
    # 2. Hitung komponen At-Bat
    bb_allowed = pa_per_game * bb_rate
    at_bats = pa_per_game - bb_allowed
    xhits_allowed = at_bats * xba
    
    # 3. Outs mentah (PA dikurangi Hit dan Walk)
    raw_xouts = pa_per_game - xhits_allowed - bb_allowed
    
    # ATURAN #3: FATIGUE PENALTY
    # Memotong ekspektasi 5% - 10% untuk antisipasi Innings Limit di akhir musim.
    # Kita ambil jalan tengah: pemotongan 7.5% (multiplier 0.925)
    fatigue_multiplier = 0.925
    final_xouts = raw_xouts * fatigue_multiplier
    
    return final_xouts

def calculate_xk(pa_per_game, k_percent):
    """Menghitung Expected Strikeouts (xK)"""
    return pa_per_game * (k_percent / 100)

def get_poisson_probability(expected_value, line, bet_type="over"):
    """
    ATURAN #4: POISSON MATH
    Mengonversi ekspektasi K atau Outs menjadi persentase probabilitas Over/Under.
    """
    # Poisson CDF bekerja dengan bilangan bulat (discrete)
    floor_line = int(line)
    
    if bet_type.lower() == "over":
        # Peluang terjadinya angka di ATAS line
        prob = 1 - poisson.cdf(floor_line, expected_value)
    else:
        # Peluang terjadinya angka di BAWAH atau SAMA DENGAN line
        prob = poisson.cdf(floor_line, expected_value)
        
    return prob * 100

def get_implied_probability(american_odds):
    """Konversi Odds Bandar ke Persentase Probabilitas"""
    if american_odds > 0:
        return 100 / (american_odds + 100) * 100
    else:
        return (-american_odds) / (-american_odds + 100) * 100
