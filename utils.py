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
            gcp_info = json.loads(st.secrets["GCP_CREDENTIALS"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                gcp_info,
                scopes=[
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
        else:
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
    Carica automaticamente tutti i file Google Sheets relativi
    al campionato scelto dall'utente.
    Ritorna:
        - DataFrame unito di tutte le stagioni
        - Nome campionato selezionato
    """

    st.sidebar.markdown("### 🌐 Origine: Google Sheets")

    client = get_gsheets_client()

    spreadsheets = client.list_spreadsheet_files()

    if not spreadsheets:
        st.warning("⚠ Nessun Google Sheet trovato nel tuo account.")
        st.stop()

    # Ricostruisce elenco macro-campionati
    campionati = set()
    for s in spreadsheets:
        nome_split = s["name"].split("_")
        if len(nome_split) >= 2:
            campionato = f"{nome_split[0]}_{nome_split[1]}"
            campionati.add(campionato)

    campionati_disponibili = sorted(list(campionati))

    if not campionati_disponibili:
        st.warning("⚠ Nessun campionato rilevato nei nomi dei Google Sheets.")
        st.stop()

    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        campionati_disponibili
    )

    # Trova tutti i Google Sheets relativi a quel campionato
    sheets_da_caricare = [
        s for s in spreadsheets
        if s["name"].upper().startswith(campionato_scelto.upper())
    ]

    if not sheets_da_caricare:
        st.warning(f"⚠ Nessun file trovato per il campionato selezionato: {campionato_scelto}")
        st.stop()

    lista_df = []

    for s in sheets_da_caricare:
        try:
            spreadsheet = client.open(s["name"])
            worksheet_names = [ws.title for ws in spreadsheet.worksheets()]

            # Carica sempre il primo foglio (o eventualmente scegli se più fogli)
            worksheet = spreadsheet.worksheet(worksheet_names[0])
            data = worksheet.get_all_records()

            if data:
                df_tmp = pd.DataFrame(data)
                df_tmp["__file"] = s["name"]
                df_tmp["country"] = campionato_scelto.upper()
                lista_df.append(df_tmp)
                st.sidebar.success(f"✅ Caricato {s['name']}")
            else:
                st.sidebar.warning(f"⚠ Il foglio {s['name']} è vuoto.")
        except Exception as e:
            st.sidebar.warning(f"⚠ Errore su {s['name']}: {e}")

    if not lista_df:
        st.error("⚠ Nessun file Google Sheet valido caricato.")
        st.stop()

    # Unisce tutti i DataFrame
    df = pd.concat(lista_df, ignore_index=True)

    # ----------------------------------------------------------
    # 🔥 NUOVO BLOCCO: pulizia Odds
    # ----------------------------------------------------------
    for col in ["Odd home", "Odd Away"]:
        if col in df.columns:
            # Rimpiazza valori vuoti o stringhe non numeriche con NaN
            df[col] = df[col].replace(["-", "nan", "NaN", ""], np.nan)

            # Trasforma le virgole in punti decimali
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )

            # Converte in numerico
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ----------------------------------------------------------
    # Selezione stagioni
    # ----------------------------------------------------------

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

    return df, campionato_scelto

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
