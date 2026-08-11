import pandas as pd

def clean_name_string(name):
    """
    ATURAN #1: ANTI-ERROR STRING MATCHING
    Membersihkan string dari spasi berlebih, format 'Last, First', dan huruf kecil.
    """
    if pd.isna(name):
        return ""
    name_str = str(name).strip().lower()
    
    # Jika formatnya 'last, first' (contoh: 'cole, gerrit'), kita balik jadi 'gerrit cole'
    if ',' in name_str:
        parts = name_str.split(',')
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name_str

def extract_clean_names(df):
    """
    Mendeteksi kolom nama di DataFrame secara dinamis dan membuat kolom 'clean_name'.
    """
    # Samakan semua nama header kolom menjadi lowercase agar tidak ada beda 'Player' vs 'player'
    df.columns = df.columns.str.strip().str.lower()
    
    if 'clean_name' in df.columns:
        return df

    # Cek berbagai kemungkinan nama header kolom nama dari Savant / Master CSV
    if 'player_name' in df.columns:
        df['clean_name'] = df['player_name'].apply(clean_name_string)
    elif 'player' in df.columns:
        df['clean_name'] = df['player'].apply(clean_name_string)
    elif 'name' in df.columns:
        df['clean_name'] = df['name'].apply(clean_name_string)
    elif 'first_name' in df.columns and 'last_name' in df.columns:
        df['clean_name'] = df.apply(
            lambda row: clean_name_string(f"{row['first_name']} {row['last_name']}"), axis=1
        )
    else:
        # Fallback: cari kolom apa saja yang mengandung kata 'name' atau 'player'
        possible_cols = [c for c in df.columns if 'name' in c or 'player' in c]
        if possible_cols:
            df['clean_name'] = df[possible_cols[0]].apply(clean_name_string)
        else:
            raise KeyError(f"Tidak dapat menemukan kolom nama pitcher. Header kolom yang ada: {list(df.columns)}")
            
    return df

def load_and_clean_data():
    """
    Meload CSV dan menstandarisasi nama pitcher.
    """
    df_rhb = pd.read_csv('data/pitcher_vs_rhb.csv')
    df_lhb = pd.read_csv('data/pitcher_vs_lhb.csv')
    df_master = pd.read_csv('data/master_pitcher2026.csv')
    
    # Terapkan pembersih fleksibel ke ketiga dataframe
    df_rhb = extract_clean_names(df_rhb)
    df_lhb = extract_clean_names(df_lhb)
    df_master = extract_clean_names(df_master)
    
    return df_master, df_rhb, df_lhb

def get_pitcher_stats(pitcher_name, df_master, df_rhb, df_lhb):
    """
    Mengambil seluruh data pitcher (Master, vs RHB, vs LHB) berdasarkan nama.
    """
    target_name = clean_name_string(pitcher_name)
    
    master_stat = df_master[df_master['clean_name'] == target_name]
    rhb_stat = df_rhb[df_rhb['clean_name'] == target_name]
    lhb_stat = df_lhb[df_lhb['clean_name'] == target_name]
    
    # Fallback jika ada perbedaan ejaan tipis
    if master_stat.empty:
        master_stat = df_master[df_master['clean_name'].str.contains(target_name, regex=False)]
        if master_stat.empty:
            return None
            
    return {
        "name": pitcher_name,
        "master": master_stat.iloc[0].to_dict(),
        "vs_rhb": rhb_stat.iloc[0].to_dict() if not rhb_stat.empty else None,
        "vs_lhb": lhb_stat.iloc[0].to_dict() if not lhb_stat.empty else None
    }
