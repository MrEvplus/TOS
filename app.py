import streamlit as st
import pandas as pd
import numpy as np
import os
from macros import run_macro_stats
from team_stats import run_team_stats
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

db_selected = st.sidebar.selectbox(
    "Seleziona Campionato (Database):",
    db_files
)

DATA_PATH = os.path.join(DATA_FOLDER, db_selected)

try:
    df = pd.read_excel(DATA_PATH, sheet_name=None)
    df = list(df.values())[0]

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(r"[\n\r\t]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )

    st.sidebar.success("✅ Database caricato automaticamente!")

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

df["goals_total"] = df["Home Goal FT"] + df["Away Goal FT"]
df["goals_1st_half"] = df["Home Goal 1T"] + df["Away Goal 1T"]
df["goals_2nd_half"] = df["goals_total"] - df["goals_1st_half"]

df["match_result"] = np.select(
    [
        df["Home Goal FT"] > df["Away Goal FT"],
        df["Home Goal FT"] == df["Away Goal FT"],
        df["Home Goal FT"] < df["Away Goal FT"]
    ],
    ["Home Win", "Draw", "Away Win"],
    default="Unknown"
)

df["btts"] = np.where(
    (df["Home Goal FT"] > 0) & (df["Away Goal FT"] > 0),
    1, 0
)

if menu_option == "Macro Stats per Campionato":
    run_macro_stats(df, db_selected)

elif menu_option == "Statistiche per Squadre":
    run_team_stats(df, db_selected)

elif menu_option == "Confronto Pre Match":
    run_pre_match()
