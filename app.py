import streamlit as st
import pandas as pd
import numpy as np
import json
from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match
from utils import load_data_from_supabase, load_data_from_file, label_match
from supabase import create_client

# -------------------------------------------------------
# CONFIGURAZIONE PAGINA
# -------------------------------------------------------
st.set_page_config(
    page_title="Trading Dashboard",
    layout="wide"
)

st.sidebar.title("📊 Trading Dashboard")

# -------------------------------------------------------
# SEZIONE UPSERT CSV -> SUPABASE
# -------------------------------------------------------

st.sidebar.markdown("### 🔄 Upload CSV su Supabase (UPsert)")

uploaded_file_upsert = st.sidebar.file_uploader(
    "Carica il file CSV da importare su Supabase:",
    type=["csv"],
    key="uploader_supabase"
)

if uploaded_file_upsert is not None:
    # Usa sep=";" per CSV separati da punto e virgola
    df_upload = pd.read_csv(uploaded_file_upsert, sep=";")
    st.sidebar.success("✅ File CSV caricato correttamente!")
    st.sidebar.write("Anteprima dati:", df_upload.head())

    # Bottone per lanciare l'upsert
    if st.sidebar.button("👉 Esegui UPsert su Supabase"):

        # -------------------------------
        # PULIZIA DATI PRIMA DELL'UPSERT
        # -------------------------------
        # Uniforma squadre in minuscolo
        if "txtechipa1" in df_upload.columns:
            df_upload["txtechipa1"] = df_upload["txtechipa1"].astype(str).str.strip().str.lower()
        if "txtechipa2" in df_upload.columns:
            df_upload["txtechipa2"] = df_upload["txtechipa2"].astype(str).str.strip().str.lower()

        # Sostituisci virgole con punti
        df_upload = df_upload.applymap(
            lambda x: str(x).replace(",", ".") if isinstance(x, str) else x
        )

        # Conversione colonne numeriche
        num_cols = ["cotaa", "cotad", "cotae"]
        for col in num_cols:
            if col in df_upload.columns:
                df_upload[col] = pd.to_numeric(df_upload[col], errors="coerce")

        # Sostituisce NaN con None nel DataFrame
        df_upload = df_upload.where(pd.notnull(df_upload), None)

        # Trasforma in lista di dict
        data = df_upload.to_dict(orient="records")

        # --------------------------------
        # FIX DEFINITIVO PER JSON NAN
        # --------------------------------
        for record in data:
            for k, v in record.items():
                if isinstance(v, float):
                    if pd.isna(v) or v in [np.inf, -np.inf]:
                        record[k] = None

        data_clean = data

        # -------------------------------
        # ESEGUE UPSERT SU SUPABASE
        # -------------------------------
        SUPABASE_URL = "https://dqqlaamfxaconepbdjek.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRxcWxhYW1meGFjb25lcGJkamVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5MTcwMTAsImV4cCI6MjA2NzQ5MzAxMH0.K9UmjDqrv-fJcl3jwdLiD5B0Md8JiTMrOAaRKz9ge_g"

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        try:
            res = supabase.table("partite") \
                .upsert(data_clean, on_conflict=["datameci", "txtechipa1", "txtechipa2"]) \
                .execute()
            st.sidebar.success("✅ UPsert completato su Supabase!")
            st.sidebar.write("Dettagli risposta Supabase:", res)
        except Exception as e:
            st.sidebar.error(f"❌ Errore durante l'UPsert su Supabase: {str(e)}")

# -------------------------------------------------------
# MENU PRINCIPALE
# -------------------------------------------------------

menu_option = st.sidebar.radio(
    "Naviga tra le sezioni:",
    [
        "Macro Stats per Campionato",
        "Statistiche per Squadre",
        "Confronto Pre Match"
    ]
)

# -------------------------------------------------------
# SELEZIONE ORIGINE DATI
# -------------------------------------------------------
origine_dati = st.sidebar.radio(
    "Seleziona origine dati:",
    ["Supabase", "Upload Manuale"]
)

if origine_dati == "Supabase":
    df, db_selected = load_data_from_supabase()
else:
    df, db_selected = load_data_from_file()

# -------------------------------------------------------
# MAPPING COLONNE COMPLETO
# -------------------------------------------------------
col_map = {
    "country": "country",
    "sezonul": "Stagione",
    "datameci": "Data",
    "orameci": "Orario",
    "etapa": "Round",
    "txtechipa1": "Home",
    "txtechipa2": "Away",
    "scor1": "Home Goal FT",
    "scor2": "Away Goal FT",
    "scorp1": "Home Goal 1T",
    "scorp2": "Away Goal 1T",
    "place1": "Posizione Classifica Generale",
    "place1a": "Posizione Classifica Home",
    "place2": "Posizione Classifica Away Generale",
    "place2d": "Posizione classifica away",
    "cotaa": "Odd home",
    "cotad": "Odd Away",
    "cotae": "Odd Draw",
    "cotao0": "odd over 0,5",
    "cotao1": "odd over 1,5",
    "cotao": "odd over 2,5",
    "cotao3": "odd over 3,5",
    "cotao4": "odd over 4,5",
    "cotau0": "odds under 0,5",
    "cotau1": "odd under 1,5",
    "cotau": "odd under 2,5",
    "cotau3": "odd under 3,5",
    "cotau4": "odd under 4,5",
    "gg": "gg",
    "ng": "ng",
    "elohomeo": "elohomeo",
    "eloawayo": "eloawayo",
    "formah": "form h",
    "formaa": "form a",
    "suth": "Tiri totali squadra HOME (full time)",
    "suth1": "Tiri squadra HOME 1 tempo",
    "suth2": "Tiri squadra HOME 2 tempo",
    "suta": "Tiri totali squadra AWAY (full time)",
    "suta1": "Tiri squadra AWAY 1 tempo",
    "suta2": "Tiri squadra AWAY 2 tempo",
    "sutht": "Tiri in porta squadra HOME (full time)",
    "sutht1": "Tiri in porta squadra HOME 1 tempo",
    "sutht2": "Tiri in porta squadra HOME 2 tempo",
    "sutat": "Tiri in porta squadra AWAY (full time)",
    "sutat1": "Tiri in porta squadra AWAY 1 tempo",
    "sutat2": "Tiri in porta squadra AWAY 2 tempo",
    "mgolh": "minuti goal segnato home",
    "gh1": "home 1 goal segnato (min)",
    "gh2": "home 2 goal segnato(min)",
    "gh3": "home 3 goal segnato(min)",
    "gh4": "home 4 goal segnato(min)",
    "gh5": "home 5 goal segnato(min)",
    "gh6": "home 6 goal segnato(min)",
    "gh7": "home 7 goal segnato(min)",
    "gh8": "home 8 goal segnato(min)",
    "gh9": "home 9 goal segnato(min)",
    "mgola": "minuti goal segnato away",
    "ga1": "1 goal away (min)",
    "ga2": "2 goal away (min)",
    "ga3": "3 goal away (min)",
    "ga4": "4 goal away (min)",
    "ga5": "5 goal away (min)",
    "ga6": "6 goal away (min)",
    "ga7": "7 goal away (min)",
    "ga8": "8 goal away (min)",
    "ga9": "9 goal away (min)",
    "stare": "stare",
    "codechipa1": "codechipa1",
    "codechipa2": "codechipa2"
}

df.rename(columns=col_map, inplace=True)

# Pulizia colonne
df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.replace(r"[\n\r\t]", "", regex=True)
    .str.replace(r"\s+", " ", regex=True)
)

# Crea colonna Label se non presente
if "Label" not in df.columns:
    df["Label"] = df.apply(label_match, axis=1)

# Filtro multi-stagione
if "Stagione" in df.columns:
    stagioni_disponibili = sorted(df["Stagione"].dropna().unique())
    stagioni_scelte = st.sidebar.multiselect(
        "Seleziona le stagioni da includere nell'analisi:",
        options=stagioni_disponibili,
        default=stagioni_disponibili
    )
    if stagioni_scelte:
        df = df[df["Stagione"].isin(stagioni_scelte)]

# Debug colonne
st.write("✅ Colonne presenti nel dataset:")
st.write(list(df.columns))

# Controllo colonna essenziale "Home"
if "Home" not in df.columns:
    st.error("⚠️ La colonna 'Home' non esiste nel dataset selezionato.")
    st.stop()

# Eventuale filtro sulla data
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

# -------------------------------------------------------
# CHIAMATA MODULI
# -------------------------------------------------------

if menu_option == "Macro Stats per Campionato":
    run_macro_stats(df, db_selected)
elif menu_option == "Statistiche per Squadre":
    run_team_stats(df, db_selected)
elif menu_option == "Confronto Pre Match":
    run_pre_match(df, db_selected)
