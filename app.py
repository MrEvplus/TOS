import streamlit as st
import pandas as pd
import numpy as np
import os
from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match
from utils import load_data_from_gsheets, label_match

# -------------------------------------------------------
# CONFIGURAZIONE PAGINA
# -------------------------------------------------------
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

# -------------------------------------------------------
# SELEZIONE ORIGINE DATI (Google Sheets o Upload Manuale)
# -------------------------------------------------------
origine_dati = st.sidebar.radio(
    "Seleziona origine dati:",
    ["Google Sheets", "Upload Manuale"]
)

# -------------------------------------------------------
# BRANCH: GOOGLE SHEETS
# -------------------------------------------------------
if origine_dati == "Google Sheets":
    df, db_selected = load_data_from_gsheets()

# -------------------------------------------------------
# BRANCH: UPLOAD MANUALE
# -------------------------------------------------------
else:
    st.sidebar.markdown("### 📂 Origine: Upload Manuale")

    DATA_FOLDER = "data"

    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

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

    db_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]

    if not db_files:
        st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
        st.stop()

    file_selected = st.sidebar.selectbox(
        "Seleziona File Excel:",
        db_files
    )

    DATA_PATH = os.path.join(DATA_FOLDER, file_selected)

    try:
        xls = pd.ExcelFile(DATA_PATH)

        st.sidebar.success("✅ Database caricato dal disco!")
        st.sidebar.write("✅ Fogli disponibili nel file Excel:")
        st.sidebar.write(xls.sheet_names)

        sheet_name = st.sidebar.selectbox(
            "Scegli il foglio da elaborare:",
            xls.sheet_names
        )

        df = pd.read_excel(DATA_PATH, sheet_name=sheet_name)

        # Trova campionati disponibili
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
            df = df[df["country"] == db_selected]
        else:
            st.error("⚠️ Nessun campionato trovato nella colonna 'country' del foglio Excel selezionato.")
            st.stop()

    except Exception as e:
        st.error(f"Errore nel caricamento file: {e}")
        st.stop()

# -------------------------------------------------------
# COMMON LOGIC (uguale per entrambe le origini)
# -------------------------------------------------------

# Pulizia nomi colonne
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

# SELEZIONE MULTI-STAGIONE
if "Stagione" in df.columns:
    stagioni_disponibili = sorted(df["Stagione"].dropna().unique())
else:
    stagioni_disponibili = []


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

# -------------------------------------------------------
# CHIAMATA MODULI
# -------------------------------------------------------

if menu_option == "Macro Stats per Campionato":
    run_macro_stats(df, db_selected)
elif menu_option == "Statistiche per Squadre":
    run_team_stats(df, db_selected)
elif menu_option == "Confronto Pre Match":
    run_pre_match(df, db_selected)
