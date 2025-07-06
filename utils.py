import numpy as np
import dropbox
import pandas as pd
import io
import streamlit as st

# Legge il token dai secrets
DROPBOX_ACCESS_TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]

def read_excel_from_dropbox(dropbox_path):
    """
    Scarica un singolo file Excel da Dropbox e lo restituisce come oggetto ExcelFile (pandas)
    """
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    _, res = dbx.files_download(path=dropbox_path)
    file_like = io.BytesIO(res.content)
    xls = pd.ExcelFile(file_like)
    return xls

def list_files_in_dropbox_folder(folder_path="/Database/"):
    """
    Elenca tutti i file presenti in una cartella Dropbox
    """
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    result = dbx.files_list_folder(folder_path)
    files = []
    for entry in result.entries:
        if isinstance(entry, dropbox.files.FileMetadata):
            files.append(entry.name)
    return files

def load_data_from_dropbox():
    """
    Carica automaticamente tutti i file Excel relativi al campionato scelto dall'utente.
    Ritorna:
        - DataFrame unito
        - Nome campionato selezionato
    """
    st.sidebar.markdown("### 🌐 Origine: Dropbox")

    DROPBOX_FOLDER = "/Database/"
    db_files = list_files_in_dropbox_folder(DROPBOX_FOLDER)

    if not db_files:
        st.warning("⚠ Nessun file trovato su Dropbox.")
        st.stop()

    # Raggruppa campionati (es. BRAZIL_1, BRAZIL_2, ecc.)
    campionati = set()
    for file in db_files:
        nome_split = file.split("_")
        if len(nome_split) >= 2:
            campionato = f"{nome_split[0].upper()}_{nome_split[1]}"
            campionati.add(campionato)
    campionati_disponibili = sorted(list(campionati))

    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        [""] + campionati_disponibili,
        index=0
    )

    if campionato_scelto == "":
        st.info("ℹ️ Seleziona un campionato per procedere al caricamento dati.")
        st.stop()

    # Filtra file
    files_da_caricare = [
        f for f in db_files
        if f.upper().startswith(campionato_scelto.upper())
    ]

    if not files_da_caricare:
        st.warning(f"⚠ Nessun file trovato per il campionato selezionato: {campionato_scelto}")
        st.stop()

    lista_df = []
    for file in files_da_caricare:
        dropbox_path = DROPBOX_FOLDER + file
        try:
            xls = read_excel_from_dropbox(dropbox_path)
            sheet_name = xls.sheet_names[0]
            df_tmp = pd.read_excel(xls, sheet_name=sheet_name)
            df_tmp["__file"] = file
            # 👇 SOVRASCRIVE IL CAMPO COUNTRY
            df_tmp["country"] = campionato_scelto
            lista_df.append(df_tmp)
            st.sidebar.success(f"✅ Caricato {file}")
        except Exception as e:
            st.sidebar.warning(f"⚠ Errore su {file}: {e}")

    if not lista_df:
        st.error("⚠ Nessun file Excel valido caricato.")
        st.stop()

    df = pd.concat(lista_df, ignore_index=True)
    st.sidebar.write(f"✅ Righe totali caricate per {campionato_scelto}: {len(df)}")

    return df, campionato_scelto

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
