import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

# -------------------------------
# Upload multipli file
# -------------------------------
st.title("Serie A Trading Dashboard")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

uploaded_file = st.file_uploader(
    "Carica uno o più database Excel:",
    type=["xlsx"],
    accept_multiple_files=False
)

if uploaded_file is not None:
    file_path = os.path.join(DATA_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    st.success("✅ File caricato e salvato!")

# -------------------------------
# Elenco file disponibili
# -------------------------------
files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]

if not files:
    st.warning("⚠ Nessun database presente nella cartella data/. Carica un file Excel per iniziare.")
    st.stop()

selected_file = st.selectbox("Seleziona Campionato (Database):", files)

DATA_PATH = os.path.join(DATA_FOLDER, selected_file)

# -------------------------------
# Lettura file selezionato
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
# Preparazione dati
# -------------------------------
# Totali goals
df["goals_total"] = df["Home Goal FT"] + df["Away Goal FT"]
df["goals_1st_half"] = df["Home Goal 1T"] + df["Away Goal 1T"]
df["goals_2nd_half"] = df["goals_total"] - df["goals_1st_half"]

# Risultato Match
df["match_result"] = np.select(
    [
        df["Home Goal FT"] > df["Away Goal FT"],
        df["Home Goal FT"] == df["Away Goal FT"],
        df["Home Goal FT"] < df["Away Goal FT"]
    ],
    ["Home Win", "Draw", "Away Win"],
    default="Unknown"
)

# BTTS
df["btts"] = np.where(
    (df["Home Goal FT"] > 0) & (df["Away Goal FT"] > 0),
    1, 0
)

# -------------------------------
# Filtra partite giocate (data)
# -------------------------------
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    today = pd.Timestamp.now().normalize()
    df_filtered = df[df["Data"] <= today]
else:
    df_filtered = df.copy()

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

# Media Totale
means = grouped.drop(columns=group_cols).mean(numeric_only=True)
means[group_cols[0]] = grouped[group_cols[0]].iloc[0] if len(grouped) else ""
means[group_cols[1]] = "DELTA"
means["Matches"] = grouped["Matches"].sum()
grouped = pd.concat([grouped, pd.DataFrame([means])], ignore_index=True)

# Decimali
cols_pct = [col for col in grouped.columns if "_pct" in col or "AvgGoals" in col]
grouped[cols_pct] = grouped[cols_pct].round(2)

st.subheader("✅ League Stats Summary")
st.dataframe(grouped, use_container_width=True)

# -------------------------------
# Distribuzione gol segnati per fasce tempo
# -------------------------------
def classify_goal_minute(minute):
    if pd.isna(minute):
        return None
    try:
        minute = int(minute)
    except:
        return None
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

def split_goal_minutes(val):
    if pd.isna(val):
        return []
    return [
        int(x.strip())
        for x in str(val).split(";")
        if x.strip().isdigit()
    ]

goal_cols_home = [
    "minuti goal home",
    "home 1 goal segnato (min)",
    "home 2 goal segnato(min)",
    "home 3 goal segnato(min)",
    "home 4 goal segnato(min)",
    "home 5 goal segnato(min)",
    "home 6 goal segnato(min)",
    "home 7 goal segnato(min)",
    "home 8 goal segnato(min)",
    "home 9 goal segnato(min)",
]

goal_cols_away = [
    "minuti goal away",
    "1 goal away (min)",
    "2 goal away (min)",
    "3 goal away (min)",
    "4 goal away (min)",
    "5 goal away (min)",
    "6 goal away (min)",
    "7 goal away (min)",
    "8 goal away (min)",
    "9 goal away (min)",
]

goal_minutes = []

for col in goal_cols_home:
    if col in df_filtered.columns:
        minutes = (
            df_filtered[col]
            .dropna()
            .apply(split_goal_minutes)
            .explode()
            .dropna()
            .astype(int)
            .apply(classify_goal_minute)
            .tolist()
        )
        goal_minutes.extend(minutes)

for col in goal_cols_away:
    if col in df_filtered.columns:
        minutes = (
            df_filtered[col]
            .dropna()
            .apply(split_goal_minutes)
            .explode()
            .dropna()
            .astype(int)
            .apply(classify_goal_minute)
            .tolist()
        )
        goal_minutes.extend(minutes)

if goal_minutes:
    goal_band_counts = pd.Series(goal_minutes).value_counts(normalize=True).sort_index()
    goal_band_perc = (goal_band_counts * 100).round(2).to_dict()

    st.subheader(f"Distribuzione gol segnati per fasce tempo - {selected_file}")
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

# -------------------------------
# League Data by Start Price
# -------------------------------
st.subheader(f"✅ League Data by Start Price - {selected_file}")

def label_match(row):
    h = row["Odd home"]
    a = row["Odd Away"]
    label = ""

    if h < 1.5:
        label = "H_StrongFav <1.5"
    elif 1.5 <= h < 2:
        label = "H_MediumFav 1.5-2"
    elif 2 <= h < 3:
        label = "H_SmallFav 2-3"
    elif h <= 3 and a <= 3:
        label = "SuperCompetitive H-A<3"
    elif a < 1.5:
        label = "A_StrongFav <1.5"
    elif 1.5 <= a < 2:
        label = "A_MediumFav 1.5-2"
    elif 2 <= a < 3:
        label = "A_SmallFav 2-3"
    else:
        label = "Others"
    return label

if "Odd home" in df_filtered.columns and "Odd Away" in df_filtered.columns:
    df_filtered["Label"] = df_filtered.apply(label_match, axis=1)

    group_label = df_filtered.groupby("Label").agg(
        Matches=("Home", "count"),
        HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean()*100),
        Draw_pct=("match_result", lambda x: (x == "Draw").mean()*100),
        AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean()*100),
        AvgGoals1T=("goals_1st_half", "mean"),
        AvgGoals2T=("goals_2nd_half", "mean"),
        AvgGoalsTotal=("goals_total", "mean"),
        Over0_5_FH_pct=("goals_1st_half", lambda x: (x > 0.5).mean()*100),
        Over1_5_FH_pct=("goals_1st_half", lambda x: (x > 1.5).mean()*100),
        Over2_5_FH_pct=("goals_1st_half", lambda x: (x > 2.5).mean()*100),
        Over0_5_FT_pct=("goals_total", lambda x: (x > 0.5).mean()*100),
        Over1_5_FT_pct=("goals_total", lambda x: (x > 1.5).mean()*100),
        Over2_5_FT_pct=("goals_total", lambda x: (x > 2.5).mean()*100),
        Over3_5_FT_pct=("goals_total", lambda x: (x > 3.5).mean()*100),
        Over4_5_FT_pct=("goals_total", lambda x: (x > 4.5).mean()*100),
        BTTS_pct=("btts", "mean")
    ).reset_index()

    group_label[cols_pct] = group_label[cols_pct].round(2)

    st.dataframe(group_label, use_container_width=True)
else:
    st.info("⚠ Quote mancanti per generare League Data by Start Price.")

