import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder

# -------------------------------
# COSTANTI
# -------------------------------
DATA_FOLDER = "data"

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

st.title("Serie A Trading Dashboard")

# -------------------------------
# CREAZIONE FOLDER
# -------------------------------
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# -------------------------------
# UPLOAD FILE
# -------------------------------
uploaded_file = st.file_uploader("Carica un nuovo database Excel:", type=["xlsx"])

if uploaded_file is not None:
    file_path = os.path.join(DATA_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    st.success(f"✅ Database {uploaded_file.name} caricato e salvato con successo!")

# -------------------------------
# SELEZIONE FILE
# -------------------------------
files_available = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]

if not files_available:
    st.warning("⚠️ Nessun database presente nella cartella data/. Carica un file Excel per iniziare.")
    st.stop()

selected_file = st.selectbox("📁 Seleziona il database Excel", files_available)

DATA_PATH = os.path.join(DATA_FOLDER, selected_file)

# -------------------------------
# LETTURA EXCEL
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

    st.success(f"✅ Database caricato automaticamente: {selected_file}")

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# -------------------------------
# FILTRI STAGIONI IN CORSO
# -------------------------------
oggi = datetime.now()

# Conversione colonna Data
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], errors='coerce', format="%d/%m/%Y")
else:
    df["Data"] = pd.NaT

df_filtered = df.copy()

# Solo partite già giocate nella stagione in corso
if "Stagione" in df.columns:
    stagioni = df["Stagione"].unique()
    for stagione in stagioni:
        mask_stagione = df_filtered["Stagione"] == stagione
        max_data_stagione = df_filtered.loc[mask_stagione, "Data"].max()

        # Se la stagione è quella in corso (anno più alto) e ci sono partite future, filtra
        if max_data_stagione is not pd.NaT and max_data_stagione > oggi:
            df_filtered = df_filtered[~((df_filtered["Stagione"] == stagione) & (df_filtered["Data"] > oggi))]

# -------------------------------
# CALCOLI BASE
# -------------------------------

# Gol totali e per tempi
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

# Aggiungi riga media
media_row = grouped.select_dtypes(include=[np.number]).mean(numeric_only=True)
media_row["country"] = grouped["country"].iloc[0] if not grouped.empty else "MEDIA"
media_row["Stagione"] = "DELTA"
media_row["Matches"] = grouped["Matches"].sum()

grouped = pd.concat([grouped, pd.DataFrame([media_row])], ignore_index=True)

# Arrotonda a 2 decimali
cols_pct = [col for col in grouped.columns if grouped[col].dtype in [float, np.float64]]
grouped[cols_pct] = grouped[cols_pct].round(2)

st.subheader("✅ League Stats Summary")
gb = GridOptionsBuilder.from_dataframe(grouped)
gb.configure_default_column(editable=False, groupable=True, filter=True, sortable=True, resizable=True)
gridOptions = gb.build()

AgGrid(grouped, gridOptions=gridOptions, theme='alpine')

# -------------------------------
# GOAL BANDS DISTRIBUTION
# -------------------------------

goal_cols_home = ["minuti goal segnato home"]
goal_cols_away = ["minuti goal segnato away"]

goal_minutes = []

for col in goal_cols_home + goal_cols_away:
    if col in df_filtered.columns:
        goal_minutes.extend(
            df_filtered[col].dropna().apply(lambda x: classify_goal_minute(x)).values
        )

goal_band_counts = pd.Series(goal_minutes).value_counts(normalize=True).sort_index()
goal_band_perc = (goal_band_counts * 100).round(2).to_dict()

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

# -------------------------------
# LEAGUE DATA BY START PRICE
# -------------------------------
def label_match(row):
    try:
        h = row["Odd home"]
        a = row["Odd Away"]

        if pd.isna(h) or pd.isna(a):
            return "Others"

        if h < 1.5:
            return "H_StrongFav"
        elif 1.5 <= h < 2:
            return "H_MediumFav"
        elif 2 <= h < 3:
            return "H_SmallFav"
        elif h <= 3 and a <= 3:
            return "SuperCompetitive H-A<3"
        elif a < 1.5:
            return "A_StrongFav"
        elif 1.5 <= a < 2:
            return "A_MediumFav"
        elif 2 <= a < 3:
            return "A_SmallFav"
        else:
            return "Others"
    except:
        return "Others"

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

    group_label[[
        col for col in group_label.columns if group_label[col].dtype in [float, np.float64]
    ]] = group_label[[
        col for col in group_label.columns if group_label[col].dtype in [float, np.float64]
    ]].round(2)

    st.subheader(f"✅ League Data by Start Price - {selected_file}")
    gb2 = GridOptionsBuilder.from_dataframe(group_label)
    gb2.configure_default_column(editable=False, groupable=True, filter=True, sortable=True, resizable=True)
    gridOptions2 = gb2.build()

    AgGrid(group_label, gridOptions=gridOptions2, theme='alpine')
else:
    st.info("⚠️ Non ci sono colonne Odd home o Odd Away nel file caricato. League Data by Start Price non calcolabile.")

# -------------------------------
# FUNZIONE PER GOAL BANDS
# -------------------------------
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
