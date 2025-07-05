import streamlit as st
import pandas as pd
import numpy as np
import os
from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match

DATA_FOLDER = "data"

st.set_page_config(
    page_title="Trading Dashboard",
    layout="wide"
)

st.sidebar.title("📊 Trading Dashboard")
menu_option = st.sidebar.radio(
    "Naviga tra le sezioni:",
    [
        "Macro Stats per Campionato",
        "Statistiche per Squadre",
        "Confronto Pre Match"
    ]
)

# Crea cartella data se non esiste
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Upload file
st.sidebar.header("📥 Upload Database")

uploaded_files = st.sidebar.file_uploader(
    "Carica uno o più database Excel:",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        save_path = os.path.join(DATA_FOLDER, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
    st.sidebar.success("✅ File caricati e salvati!")

# Lista file presenti
db_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]
if not db_files:
    st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
    st.stop()

# Seleziona database
file_selected = st.sidebar.selectbox(
    "Seleziona File Excel:",
    db_files
)

DATA_PATH = os.path.join(DATA_FOLDER, file_selected)

try:
    # Carica Excel per vedere i fogli disponibili
    xls = pd.ExcelFile(DATA_PATH)

    st.sidebar.success("✅ Database caricato automaticamente!")
    st.sidebar.write("✅ Fogli disponibili nel file Excel:")
    st.sidebar.write(xls.sheet_names)

    # Permetti scelta foglio
    sheet_name = st.sidebar.selectbox(
        "Scegli il foglio da elaborare:",
        xls.sheet_names
    )

    # Leggi il foglio selezionato
    df = pd.read_excel(DATA_PATH, sheet_name=sheet_name)

    # Pulisci nomi colonne
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(r"[\n\r\t]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )

    st.sidebar.success("✅ Foglio Excel caricato correttamente!")

    from utils import label_match

    if "Label" not in df.columns:
        df["Label"] = df.apply(label_match, axis=1)

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# Normalizza e trova campionati
if "country" in df.columns:
    df["country"] = (
        df["country"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    campionati_disponibili = sorted(df["country"].unique())
else:
    campionati_disponibili = []

if campionati_disponibili:
    db_selected = st.sidebar.selectbox(
        "Seleziona Campionato:",
        campionati_disponibili
    )
else:
    st.error("⚠️ Nessun campionato trovato nella colonna 'country' del foglio Excel selezionato.")
    st.stop()

# Mostra colonne disponibili per debug
st.write("✅ Colonne presenti nel foglio selezionato:")
st.write(list(df.columns))

# Controllo colonna essenziale "Home"
if "Home" not in df.columns:
    st.error("⚠️ La colonna 'Home' non esiste nel foglio selezionato. Controlla che il file Excel sia corretto.")
    st.stop()

# Eventuale filtro sulla data
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

# Chiamata al modulo selezionato
if menu_option == "Macro Stats per Campionato":
    run_macro_stats(df, db_selected)

elif menu_option == "Statistiche per Squadre":
    run_team_stats(df, db_selected)

elif menu_option == "Confronto Pre Match":
    run_pre_match(df, db_selected)
