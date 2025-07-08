import numpy as np
import pandas as pd
import streamlit as st
from supabase import create_client

# ----------------------------------------------------------
# Connessione Supabase
# ----------------------------------------------------------

def load_data_from_supabase():
    st.sidebar.markdown("### 🌐 Origine: Supabase")

    SUPABASE_URL = "https://dqqlaamfxaconepbdjek.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRxcWxhYW1meGFjb25lcGJkamVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5MTcwMTAsImV4cCI6MjA2NzQ5MzAxMH0.K9UmjDqrv-fJcl3jwdLiD5B0Md8JiTMrOAaRKz9ge_g"

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Scarica tutti i dati dalla tabella
    res = supabase.table("partite").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        st.warning("⚠ Nessun dato trovato su Supabase.")
        st.stop()

    # Conversione eventuali virgole in punti
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(",", ".")

    # Tentativo di conversione numerica
    df = df.apply(pd.to_numeric, errors="ignore")

    # Conversione date
    if "datameci" in df.columns:
        df["datameci"] = pd.to_datetime(df["datameci"], errors="coerce")

    # Campionati disponibili
    if "country" in df.columns:
        campionati_disponibili = sorted(df["country"].dropna().unique())
    else:
        campionati_disponibili = []

    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        [""] + campionati_disponibili,
        key="selectbox_campionato_supabase"
    )

    if campionato_scelto == "":
        st.info("ℹ️ Seleziona un campionato per procedere.")
        st.stop()

    df_filtered = df[df["country"] == campionato_scelto]

    # Stagioni disponibili
    if "sezonul" in df_filtered.columns:
        stagioni_disponibili = sorted(df_filtered["sezonul"].dropna().unique())
    else:
        stagioni_disponibili = []

    stagioni_scelte = st.sidebar.multiselect(
        "Seleziona le stagioni da includere nell'analisi:",
        options=stagioni_disponibili,
        default=stagioni_disponibili,
        key="multiselect_stagioni_supabase"
    )

    if stagioni_scelte:
        df_filtered = df_filtered[df_filtered["sezonul"].isin(stagioni_scelte)]

    st.sidebar.write(f"✅ Righe caricate da Supabase: {len(df_filtered)}")

    return df_filtered, campionato_scelto

# ----------------------------------------------------------
# Upload Manuale (Excel o CSV)
# ----------------------------------------------------------

def load_data_from_file():
    st.sidebar.markdown("### 📂 Origine: Upload Manuale")

    uploaded_file = st.sidebar.file_uploader(
        "Carica il tuo file Excel o CSV:",
        type=["xls", "xlsx", "csv"],
        key="file_uploader_upload"
    )

    if uploaded_file is None:
        st.info("ℹ️ Carica un file per continuare.")
        st.stop()

    # Riconosce CSV o Excel
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(",", ".")

    df = df.apply(pd.to_numeric, errors="ignore")

    if "datameci" in df.columns:
        df["datameci"] = pd.to_datetime(df["datameci"], errors="coerce")

    if "country" in df.columns:
        campionati_disponibili = sorted(df["country"].dropna().unique())
    else:
        campionati_disponibili = []

    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        [""] + campionati_disponibili,
        key="selectbox_campionato_upload"
    )

    if campionato_scelto == "":
        st.info("ℹ️ Seleziona un campionato per procedere.")
        st.stop()

    df_filtered = df[df["country"] == campionato_scelto]

    if "sezonul" in df_filtered.columns:
        stagioni_disponibili = sorted(df_filtered["sezonul"].dropna().unique())
    else:
        stagioni_disponibili = []

    stagioni_scelte = st.sidebar.multiselect(
        "Seleziona le stagioni da includere nell'analisi:",
        options=stagioni_disponibili,
        default=stagioni_disponibili,
        key="multiselect_stagioni_upload"
    )

    if stagioni_scelte:
        df_filtered = df_filtered[df_filtered["sezonul"].isin(stagioni_scelte)]

    st.sidebar.write(f"✅ Righe caricate da Upload Manuale: {len(df_filtered)}")

    return df_filtered, campionato_scelto

# ----------------------------------------------------------
# label_match
# ----------------------------------------------------------

def label_match(row):
    h = row.get("cotaa", np.nan)
    a = row.get("cotae", np.nan)
    if np.isnan(h) or np.isnan(a):
        return "Others"
    if h < 1.5:
        return "H_StrongFav <1.5"
    elif 1.5 <= h < 2:
        return "H_MediumFav 1.5-2"
    elif 2 <= h < 3:
        return "H_SmallFav 2-3"
    elif h <= 3 and a <= 3:
        return "SuperCompetitive H-A<3"
    elif a < 1.5:
        return "A_StrongFav <1.5"
    elif 1.5 <= a < 2:
        return "A_MediumFav 1.5-2"
    elif 2 <= a < 3:
        return "A_SmallFav 2-3"
    else:
        return "Others"

# ----------------------------------------------------------
# extract_minutes
# ----------------------------------------------------------

def extract_minutes(series):
    all_minutes = []
    for val in series.dropna():
        if isinstance(val, str):
            for part in val.replace(",", ";").split(";"):
                part = part.strip()
                if part.isdigit():
                    all_minutes.append(int(part))
    return all_minutes
