import streamlit as st
import pandas as pd
import numpy as np
import os
from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match
from utils import read_excel_from_dropbox, list_files_in_dropbox_folder, label_match

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
# SELEZIONE ORIGINE DATI (Dropbox o Locale)
# -------------------------------------------------------
origine_dati = st.sidebar.radio(
    "Seleziona origine dati:",
    ["Dropbox", "Upload Manuale"]
)

# -------------------------------------------------------
# BRANCH: DROPBOX
# -------------------------------------------------------
if origine_dati == "Dropbox":
    st.sidebar.markdown("### 🌐 Origine: Dropbox")

    DROPBOX_FOLDER = "/Database/"

    # Lista file su Dropbox
    db_files = list_files_in_dropbox_folder(DROPBOX_FOLDER)

    if not db_files:
        st.warning("⚠ Nessun file trovato su Dropbox.")
        st.stop()

    lista_df = []
    for file in db_files:
        dropbox_path = DROPBOX_FOLDER + file
        try:
            xls = read_excel_from_dropbox(dropbox_path)
            # Supponiamo ci sia solo 1 foglio in ogni Excel
            foglio = xls.sheet_names[0]
            df_tmp = pd.read_excel(xls, sheet_name=foglio)
            df_tmp["__file"] = file  # traccia il file di origine
            lista_df.append(df_tmp)
            st.sidebar.success(f"✅ Caricato {file}")
        except Exception as e:
            st.warning(f"⚠ Errore nel leggere {file}: {e}")

    if not lista_df:
        st.error("⚠ Nessun Excel valido caricato.")
        st.stop()

    df = pd.concat(lista_df, ignore_index=True)

    st.sidebar.write(f"✅ Righe totali caricate da Dropbox: {len(df)}")


# -------------------------------------------------------
# BRANCH: UPLOAD MANUALE
# -------------------------------------------------------
else:
    st.sidebar.markdown("### 📂 Origine: Upload Manuale")

    DATA_FOLDER = "data"

    # Crea cartella se non esiste
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

    # Leggi lista file disponibili localmente
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

# 1. SELEZIONE CAMPIONATO
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

# 2. SELEZIONE MULTI-STAGIONE (dopo il filtro sul campionato)
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
    if not stagioni_scelte:
        stagioni_scelte = stagioni_disponibili

    df = df[df["Stagione"].isin(stagioni_scelte)]

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
