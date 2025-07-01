import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

# -------------------------------
# Titolo e upload
# -------------------------------
st.title("Serie A Trading Dashboard")

# crea cartella data se non esiste
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Upload multiplo
uploaded_files = st.file_uploader(
    "Carica uno o più database Excel:",
    type=["xlsx"],
    accept_multiple_files=True
)

# Salva file caricati
if uploaded_files:
    for uploaded_file in uploaded_files:
        save_path = os.path.join(DATA_FOLDER, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    st.success("✅ File caricati e salvati!")

# Trova tutti i file excel salvati
available_files = [
    f for f in os.listdir(DATA_FOLDER)
    if f.endswith(".xlsx")
]

# Dropdown per scegliere file
if available_files:
    selected_file = st.selectbox(
        "Seleziona Campionato (Database):",
        available_files
    )
else:
    st.warning("⚠ Nessun database caricato. Carica almeno un file Excel per iniziare.")
    st.stop()

# -------------------------------
# Caricamento file selezionato
# -------------------------------
DATA_PATH = os.path.join(DATA_FOLDER, selected_file)

try:
    df = pd.read_excel(DATA_PATH, sheet_name=None)
    df = list(df.values())[0]
    df.columns = (
        df.columns.astype(str)
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
# Filtra solo partite giocate
# -------------------------------

# se esistono le colonne Data e Orario, filtra le righe future
if "Data" in df.columns and "Orario" in df.columns:
    try:
        df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
        today = pd.to_datetime(datetime.today().strftime("%d/%m/%Y"))
        df_filtered = df[df["Data"] <= today].copy()
    except Exception as e:
        st.warning(f"⚠ Errore nel parsing delle date: {e}")
        df_filtered = df.copy()
else:
    df_filtered = df.copy()

# -------------------------------
# Preparazione colonne di calcolo
# -------------------------------
df_filtered["goals_total"] = df_filtered["Home Goal FT"] + df_filtered["Away Goal FT"]
df_filtered["goals_1st_half"] = df_filtered["Home Goal 1T"] + df_filtered["Away Goal 1T"]
df_filtered["goals_2nd_half"] = df_filtered["goals_total"] - df_filtered["goals_1st_half"]

# Esito match
df_filtered["match_result"] = np.select(
    [
        df_filtered["Home Goal FT"] > df_filtered["Away Goal FT"],
        df_filtered["Home Goal FT"] == df_filtered["Away Goal FT"],
        df_filtered["Home Goal FT"] < df_filtered["Away Goal FT"],
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
# League Stats Summary
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
    BTTS_pct=("btts", "mean"),
).reset_index()

# Media finale
if not grouped.empty:
    numeric_cols = grouped.select_dtypes(include=[np.number]).columns
    media_row = grouped[numeric_cols].mean(numeric_only=True).round(2)
    media_row["country"] = grouped["country"].iloc[0]
    media_row["Stagione"] = "DELTA"
    grouped = pd.concat([grouped, pd.DataFrame([media_row])], ignore_index=True)

# Arrotonda decimali
cols_pct = [col for col in grouped.columns if "_pct" in col or "AvgGoals" in col]
grouped[cols_pct] = grouped[cols_pct].round(2)

st.subheader("✅ League Stats Summary")
st.dataframe(grouped, use_container_width=True)

# -------------------------------
# Distribuzione gol segnati per fasce tempo
# -------------------------------

def extract_goal_minutes(series):
    """Estrae tutti i minuti da una Series che contiene stringhe separate da ;"""
    minutes = []
    for val in series.dropna():
        val_str = str(val).strip()
        if val_str == "":
            continue
        for part in val_str.split(";"):
            part = part.strip()
            if part.isdigit():
                minutes.append(int(part))
    return minutes

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

goal_minutes = []

if "minuti goal segnato home" in df_filtered.columns:
    goal_minutes += extract_goal_minutes(df_filtered["minuti goal segnato home"])

if "minuti goal segnato away" in df_filtered.columns:
    goal_minutes += extract_goal_minutes(df_filtered["minuti goal segnato away"])

if goal_minutes:
    goal_bands = pd.Series(goal_minutes).map(classify_goal_minute).value_counts(normalize=True).sort_index()
    goal_band_perc = (goal_bands * 100).round(2).to_dict()
else:
    goal_band_perc = {}

st.subheader(f"Distribuzione gol segnati per fasce tempo – {selected_file}")

if goal_band_perc:
    df_chart = pd.DataFrame({
        "Time Band": list(goal_band_perc.keys()),
        "Percentage": list(goal_band_perc.values())
    })
    fig = px.bar(
        df_chart,
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

# -------------------------------
# League Data by Start Price
# -------------------------------

st.subheader(f"✅ League Data by Start Price - {selected_file}")

def label_match(row):
    h = row.get("Odd home", np.nan)
    a = row.get("Odd Away", np.nan)
    if pd.isna(h) or pd.isna(a):
        return "Unknown"

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

if "Odd home" in df_filtered.columns and "Odd Away" in df_filtered.columns:
    df_filtered["Label"] = df_filtered.apply(label_match, axis=1)

    group_label = df_filtered.groupby("Label").agg(
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
        BTTS_pct=("btts", "mean"),
    ).reset_index()

    group_label[cols_pct] = group_label[cols_pct].round(2)
    st.dataframe(group_label, use_container_width=True)
else:
    st.info("⚠ Il file selezionato non contiene le colonne Odd home e Odd Away.")

