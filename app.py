import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime

# -------------------------------
# COSTANTI
# -------------------------------
DATA_FOLDER = "data"
DB_FILES = []

st.set_page_config(page_title="Trading Dashboard", layout="wide")

# -------------------------------
# TITOLO APP
# -------------------------------
st.title("Trading Dashboard")

# -------------------------------
# CREAZIONE CARTELLA DATA
# -------------------------------
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# -------------------------------
# UPLOAD FILE
# -------------------------------
uploaded_file = st.file_uploader(
    "Carica un nuovo database Excel:",
    type=["xlsx"],
    help="Limite 200MB per file"
)

if uploaded_file is not None:
    file_path = os.path.join(DATA_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    st.success(f"✅ File `{uploaded_file.name}` caricato con successo!")

# -------------------------------
# SELEZIONE FILE DA USARE
# -------------------------------
all_files = DB_FILES
for f in os.listdir(DATA_FOLDER):
    if f.endswith(".xlsx") and f not in all_files:
        all_files.append(f)

if not all_files:
    st.warning("⚠ Nessun database presente. Carica almeno un file Excel per iniziare.")
    st.stop()

selected_file = st.selectbox("📂 Seleziona il database da analizzare:", all_files)

DATA_PATH = os.path.join(DATA_FOLDER, selected_file)

# -------------------------------
# LETTURA FILE EXCEL
# -------------------------------
try:
    df = pd.read_excel(DATA_PATH, sheet_name=None)
    df = list(df.values())[0]

    # Pulizia nomi colonne
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(r"[\n\r\t]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )

    st.success("✅ Database caricato automaticamente!")
    st.write("Colonne presenti nel database:")
    st.write(df.columns.tolist())

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# -------------------------------
# FILTRO STAGIONE CORRENTE
# -------------------------------
# Se la stagione corrente è selezionata,
# considera solo partite fino alla data odierna
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)

today = pd.Timestamp.today().normalize()
stagione_corrente = df["Stagione"].max()

mask_corrente = ~(
    (df["Stagione"] == stagione_corrente) &
    (df["Data"] > today)
)

df_filtered = df.loc[mask_corrente]

# -------------------------------
# CALCOLI BASE
# -------------------------------
df_filtered["goals_total"] = df_filtered["Home Goal FT"] + df_filtered["Away Goal FT"]
df_filtered["goals_1st_half"] = df_filtered["Home Goal 1T"] + df_filtered["Away Goal 1T"]
df_filtered["goals_2nd_half"] = df_filtered["goals_total"] - df_filtered["goals_1st_half"]

# Esito match
df_filtered["match_result"] = np.select(
    [
        df_filtered["Home Goal FT"] > df_filtered["Away Goal FT"],
        df_filtered["Home Goal FT"] == df_filtered["Away Goal FT"],
        df_filtered["Home Goal FT"] < df_filtered["Away Goal FT"]
    ],
    ["Home Win", "Draw", "Away Win"],
    default="Unknown"
)

# BTTS
df_filtered["btts"] = np.where(
    (df_filtered["Home Goal FT"] > 0) & (df_filtered["Away Goal FT"] > 0),
    1, 0
)

# -------------------------------
# GOAL BANDS (SOLO GOAL SEGNATI)
# -------------------------------
goal_cols_home = [
    "home 1 goal segnato (min)",
    "home 2 goal segnato(min)",
    "home 3 goal segnato(min)",
    "home 4 goal segnato(min)",
    "home 5 goal segnato(min)",
    "home 6 goal segnato(min)",
    "home 7 goal segnato(min)",
    "home 8 goal segnato(min)",
    "home 9 goal segnato(min)"
]

goal_cols_away = [
    "1 goal away (min)",
    "2 goal away (min)",
    "3 goal away (min)",
    "4 goal away (min)",
    "5 goal away (min)",
    "6 goal away (min)",
    "7 goal away (min)",
    "8 goal away (min)",
    "9 goal away (min)"
]

goal_cols = [c for c in goal_cols_home + goal_cols_away if c in df_filtered.columns]

goal_minutes = []
for col in goal_cols:
    goal_minutes.extend(
        df_filtered[col].dropna().apply(
            lambda x: int(x) if pd.notna(x) and str(x).strip().isdigit() else None
        ).dropna()
    )

def classify_goal_minute(minute):
    if pd.isna(minute):
        return None
    minute = int(minute)
    if minute <= 15:
        return "0-15"
    elif minute <= 30:
        return "16-30"
    elif minute <= 45:
        return "31-45"
    elif minute <= 60:
        return "46-60"
    elif minute <= 75:
        return "60-75"
    else:
        return "76-90"

goal_band_counts = pd.Series(
    [classify_goal_minute(m) for m in goal_minutes]
).value_counts(normalize=True).sort_index()

goal_band_perc = (goal_band_counts * 100).round(2).to_dict()

# -------------------------------
# LEAGUE STATS SUMMARY
# -------------------------------
group_cols = ["country", "Stagione"]

grouped = df_filtered.groupby(group_cols).agg(
    Matches=("Home", "count"),
    HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean() * 100),
    Draw_pct=("match_result", lambda x: (x == "Draw").mean() * 100),
    AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean() * 100),
    AvgGoals1T=("goals_1st_half", "mean"),
    AvgGoals2T=("goals_2nd_half", "mean"),
    AvgGoalsTotal=("goals_total", "mean"),
    Over0_5_FH_pct=("goals_1st_half", lambda x: (x > 0.5).mean() * 100),
    Over1_5_FH_pct=("goals_1st_half", lambda x: (x > 1.5).mean() * 100),
    Over2_5_FH_pct=("goals_1st_half", lambda x: (x > 2.5).mean() * 100),
    Over0_5_FT_pct=("goals_total", lambda x: (x > 0.5).mean() * 100),
    Over1_5_FT_pct=("goals_total", lambda x: (x > 1.5).mean() * 100),
    Over2_5_FT_pct=("goals_total", lambda x: (x > 2.5).mean() * 100),
    Over3_5_FT_pct=("goals_total", lambda x: (x > 3.5).mean() * 100),
    Over4_5_FT_pct=("goals_total", lambda x: (x > 4.5).mean() * 100),
    BTTS_pct=("btts", "mean")
).reset_index()

# Media finale per tutte le stagioni
media_row = grouped.drop(columns=["country", "Stagione"]).mean()
media_row["country"] = grouped["country"].iloc[0]
media_row["Stagione"] = "DELTA"
media_row["Matches"] = grouped["Matches"].sum()

grouped = pd.concat([grouped, pd.DataFrame([media_row])], ignore_index=True)

# Arrotonda a 2 cifre
cols_to_round = grouped.select_dtypes(include=[np.number]).columns
grouped[cols_to_round] = grouped[cols_to_round].round(2)

# -------------------------------
# VISUALIZZAZIONE
# -------------------------------
st.subheader("✅ League Stats Summary")
st.dataframe(grouped, use_container_width=True)

# -------------------------------
# GRAFICO GOAL BANDS
# -------------------------------
st.subheader(f"Distribuzione gol segnati per fasce tempo - {selected_file}")

if goal_band_perc:
    chart_data = pd.DataFrame({
        "Time Band": list(goal_band_perc.keys()),
        "Percentage": list(goal_band_perc.values())
    })

    fig = px.bar(
        chart_data,
        x="Time Band",
        y="Percentage",
        text="Percentage",
        color="Time Band",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(yaxis_title="% Goals", xaxis_title="Time Band")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⚠ Nessun dato sui minuti dei gol nel file caricato.")
