import pandas as pd
import io

def clean_name_string(name):
    """Membersihkan string nama dari spasi dan format 'Last, First'"""
    if pd.isna(name):
        return ""
    name_str = str(name).strip().lower()
    
    if ',' in name_str:
        parts = name_str.split(',')
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name_str

def clean_savant_csv(filepath):
    """
    PENYELAMAT DATA: Memperbaiki format CSV Savant yang korup.
    Menghancurkan bungkus kutip raksasa agar kolom terpisah dengan benar.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Jika seluruh baris dibungkus kutip ganda (korupsi format)
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]  # Buang kutip paling luar
            line = line.replace('""', '"')  # Perbaiki kutip di dalam
        cleaned_lines.append(line)
        
    # Gabungkan kembali baris yang sudah bersih dan baca normal
    csv_data = '\n'.join(cleaned_lines)
    df = pd.read_csv(io.StringIO(csv_data))
    
    # Hapus spasi tak kasatmata dan jadikan header huruf kecil semua
    df.columns = df.columns.str.replace('"', '').str.strip().str.lower()
    return df

def extract_clean_names(df):
    """Mencari kolom nama secara otomatis dari CSV yang sudah dibersihkan"""
    if 'clean_name' in df.columns:
        return df

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
        raise KeyError(f"Kolom nama tidak ditemukan. Header yang berhasil dibaca: {list(df.columns)}")
            
    return df

def load_and_clean_data():
    # Gunakan pembersih CSV mutlak kita alih-alih pd.read_csv biasa
    df_rhb = clean_savant_csv('data/pitcher_vs_rhb.csv')
    df_lhb = clean_savant_csv('data/pitcher_vs_lhb.csv')
    df_master = clean_savant_csv('data/master_pitcher2026.csv')
    
    df_rhb = extract_clean_names(df_rhb)
    df_lhb = extract_clean_names(df_lhb)
    df_master = extract_clean_names(df_master)
    
    return df_master, df_rhb, df_lhb

def get_pitcher_stats(pitcher_name, df_master, df_rhb, df_lhb):
    target_name = clean_name_string(pitcher_name)
    
    master_stat = df_master[df_master['clean_name'] == target_name]
    rhb_stat = df_rhb[df_rhb['clean_name'] == target_name]
    lhb_stat = df_lhb[df_lhb['clean_name'] == target_name]
    
    if master_stat.empty:
        # Fallback pencarian parsial jika ejaan sedikit meleset
        master_stat = df_master[df_master['clean_name'].str.contains(target_name, regex=False)]
        if master_stat.empty:
            return None
            
    return {
        "name": pitcher_name,
        "master": master_stat.iloc[0].to_dict(),
        "vs_rhb": rhb_stat.iloc[0].to_dict() if not rhb_stat.empty else None,
        "vs_lhb": lhb_stat.iloc[0].to_dict() if not lhb_stat.empty else None
    }
