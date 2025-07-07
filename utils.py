import numpy as np
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ----------------------------------------------------------
# Legge le credenziali Google Sheets
# ----------------------------------------------------------

def get_gsheets_client():
    """
    Restituisce un client gspread autorizzato.
    Funziona sia in locale che su Streamlit Cloud.
    """
    try:
        if "GCP_CREDENTIALS" in st.secrets:
            # Se su Streamlit Cloud
            gcp_info = json.loads(st.secrets["GCP_CREDENTIALS"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                gcp_info,
                scopes=[
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
        else:
            # Se locale
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                "tradingdashboard-465220-562e2e145916.json",
                scopes=[
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
    except Exception as e:
        st.error(f"Errore nella lettura delle credenziali Google Sheets: {e}")
        st.stop()

    client = gspread.authorize(creds)
    return client

# ----------------------------------------------------------
# Carica i dati da Google Sheets
# ----------------------------------------------------------

def load_data_from_gsheets():
    """
    Carica automaticamente tutti i dati relativi al campionato scelto dall'utente
    da Google Sheets.
    Ritorna:
        - DataFrame unito
        - Nome campionato selezionato
    """

    st.sidebar.markdown("### 🌐 Origine: Google Sheets")

    client = get_gsheets_client()

    # Elenco di tutti gli spreadsheets
    spreadsheets = client.list_spreadsheet_files()

    if not spreadsheets:
        st.warning("⚠ Nessun Google Sheet trovato nel tuo account.")
        st.stop()

    # Elenco nomi file (nome foglio = campionato)
    sheet_names = [s['name'] for s in spreadsheets]

    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        [""] + sheet_names,
        index=0
    )

    if campionato_scelto == "":
        st.info("ℹ️ Seleziona un campionato per procedere al caricamento dati.")
        st.stop()

    # Apre lo spreadsheet scelto
    spreadsheet = client.open(campionato_scelto)

    worksheet_names = [ws.title for ws in spreadsheet.worksheets()]

    # Se ci sono più fogli nel file Excel → scegli quale
    foglio_excel = st.sidebar.selectbox(
        "Seleziona Foglio:",
        worksheet_names
    )

    worksheet = spreadsheet.worksheet(foglio_excel)

    data = worksheet.get_all_records()

    if not data:
        st.warning(f"⚠ Nessun dato trovato nel foglio '{foglio_excel}'.")
        st.stop()

    df = pd.DataFrame(data)

    # Trova tutti i campionati disponibili se esiste la colonna 'country'
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
            "Seleziona Campionato (colonna country):",
            campionati_disponibili
        )
        df = df[df["country"] == db_selected]
    else:
        db_selected = campionato_scelto

    # Selezione stagioni
    if "Stagione" in df.columns:
        stagioni_disponibili = sorted(df["Stagione"].dropna().unique())
    else:
        stagioni_disponibili = []

    if stagioni_disponibili:
        stagioni_scelte = st.sidebar.multiselect(
            "Seleziona le stagioni da includere nell'analisi:",
            options=stagioni_disponibili,
            default=stagioni_disponibili
        )
        if stagioni_scelte:
            df = df[df["Stagione"].isin(stagioni_scelte)]

    st.sidebar.write(f"✅ Righe caricate da Google Sheets: {len(df)}")

    return df, db_selected

# ----------------------------------------------------------
# Altre funzioni originali (label_match, extract_minutes)
# ----------------------------------------------------------

def label_match(row):
    h = row.get("Odd home", np.nan)
    a = row.get("Odd Away", np.nan)
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

def extract_minutes(series):
    all_minutes = []
    for val in series.dropna():
        if isinstance(val, str):
            for part in val.replace(",", ";").split(";"):
                part = part.strip()
                if part.isdigit():
                    all_minutes.append(int(part))
    return all_minutes
