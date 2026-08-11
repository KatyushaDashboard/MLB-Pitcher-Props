from scipy.stats import poisson

def apply_fatigue_penalty(expected_outs):
    """ATURAN #3: FATIGUE PENALTY (7.5% pemotongan outs)"""
    return expected_outs * 0.925

def calculate_xk(pa_per_game, k_percent):
    """Menghitung Expected Strikeouts (xK)"""
    return pa_per_game * (float(k_percent) / 100.0)

def calculate_xbb(pa_per_game, bb_percent):
    """Menghitung Expected Walks / Base on Balls (xBB)"""
    return pa_per_game * (float(bb_percent) / 100.0)

def calculate_xouts(pa_per_game, bb_percent, xba):
    """Menghitung Expected Outs dengan Fatigue Penalty"""
    bb_allowed = calculate_xbb(pa_per_game, bb_percent)
    at_bats = pa_per_game - bb_allowed
    xhits_allowed = at_bats * float(xba)
    
    raw_xouts = pa_per_game - xhits_allowed - bb_allowed
    return apply_fatigue_penalty(raw_xouts)

def calculate_xhits(pa_per_game, bb_percent, xba):
    """Menghitung Expected Hits Allowed (xHits)"""
    bb_allowed = calculate_xbb(pa_per_game, bb_percent)
    at_bats = pa_per_game - bb_allowed
    return at_bats * float(xba)

def calculate_xer(xouts, xwoba):
    """
    Menghitung Expected Earned Runs (xER) menggunakan skala xwOBA ke xERA.
    """
    # Konversi xwOBA ke perkiraan xERA (skala sabermetrik)
    xera = max(1.5, (float(xwoba) * 12.0) - 0.25)
    expected_ip = xouts / 3.0
    return (expected_ip * xera) / 9.0

def get_poisson_probability(expected_value, line, bet_type="over"):
    """ATURAN #4: POISSON MATH untuk probabilitas O/U"""
    floor_line = int(line)
    
    if bet_type.lower() == "over":
        prob = 1 - poisson.cdf(floor_line, expected_value)
    else:
        prob = poisson.cdf(floor_line, expected_value)
        
    return prob * 100.0

def get_implied_probability(american_odds):
    """Konversi Odds Bandar ke Probabilitas Persentase"""
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0) * 100.0
    else:
        return (-american_odds) / (-american_odds + 100.0) * 100.0
