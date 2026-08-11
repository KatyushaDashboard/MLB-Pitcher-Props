import pandas as pd

def clean_name_string(name):
    """
    ATURAN #1: ANTI-ERROR STRING MATCHING
    Membersihkan string dari spasi berlebih dan menjadikannya huruf kecil.
    """
    if pd.isna(name):
        return ""
    return str(name).strip().lower()

def format_savant_name(savant_name):
    """
    Mengubah format "Last, First" (contoh: "Cole, Gerrit") 
    menjadi "First Last" ("gerrit cole") untuk data splits.
    """
    cleaned = clean_name_string(savant_name)
    if ',' in cleaned:
        parts = cleaned.split(',')
        # parts[0] = Last, parts[1] = First
        return f"{parts[1].strip()} {parts[0].strip()}"
    return cleaned

def load_and_clean_data():
    """
    Meload CSV dan menstandarisasi nama pitcher ke dalam kolom baru 'clean_name'
    agar bisa di-lookup dengan 100% akurasi.
    """
    # 1. Load Splits Data (L60)
    df_rhb = pd.read_csv('data/pitcher_vs_rhb.csv')
    df_lhb = pd.read_csv('data/pitcher_vs_lhb.csv')
    
    # Terapkan pembersih string ke kolom 'player_name'
    df_rhb['clean_name'] = df_rhb['player_name'].apply(format_savant_name)
    df_lhb['clean_name'] = df_lhb['player_name'].apply(format_savant_name)
    
    # 2. Load Master Data (Full Season)
    df_master = pd.read_csv('data/master_pitcher2026.csv')
    
    # Gabungkan 'first_name' dan 'last_name' lalu bersihkan
    df_master['clean_name'] = df_master.apply(
        lambda row: clean_name_string(f"{row['first_name']} {row['last_name']}"), 
        axis=1
    )
    
    return df_master, df_rhb, df_lhb

def get_pitcher_stats(pitcher_name, df_master, df_rhb, df_lhb):
    """
    Mengambil seluruh data pitcher (Master, vs RHB, vs LHB) hanya dengan modal nama.
    """
    target_name = clean_name_string(pitcher_name)
    
    # Mencari data dengan metode aman
    master_stat = df_master[df_master['clean_name'] == target_name]
    rhb_stat = df_rhb[df_rhb['clean_name'] == target_name]
    lhb_stat = df_lhb[df_lhb['clean_name'] == target_name]
    
    # Jika pitcher tidak ditemukan di master, kembalikan None
    if master_stat.empty:
        return None
        
    return {
        "name": pitcher_name,
        "master": master_stat.iloc[0].to_dict(),
        "vs_rhb": rhb_stat.iloc[0].to_dict() if not rhb_stat.empty else None,
        "vs_lhb": lhb_stat.iloc[0].to_dict() if not lhb_stat.empty else None
    }
