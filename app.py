import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
import os
import datetime

# -------------------------------
# CONFIGURAZIONE
# -------------------------------

DATA_FOLDER = "data"

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")
st.title("Serie A Trading Dashboard")

# -------------------------------
# UPLOAD FILE MULTIPLI
# -------------------------------

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

uploaded_files = st.file_uploader(
    "Carica uno o più database Excel:",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        save_path = os.path.join(DATA_FOLDER, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
    st.success("✅ File caricati e salvati!")

# Lista file
db_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]
if not db_files:
    st.warning("⚠ Nessun database presente. Carica un file Excel per iniziare.")
    st.stop()

db_selected = st.selectbox(
    "Seleziona Campionato (Database):",
    db_files
)

DATA_PATH = os.path.join(DATA_FOLDER, db_selected)

# -------------------------------
# CARICAMENTO FILE
# -------------------------------

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

    st.success("✅ Database caricato automaticamente!")
    st.write("Colonne presenti nel database:")
    st.write(df.columns.tolist())

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# -------------------------------
# FILTRO PARTITE GIOCATE
# -------------------------------

if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

# -------------------------------
# CALCOLI BASE
# -------------------------------

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

# -------------------------------
# LEAGUE STATS SUMMARY
# -------------------------------

group_cols = ["country", "Stagione"]

grouped = df.groupby(group_cols).agg(
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
media_row = grouped.drop(columns=["country", "Stagione"]).mean(numeric_only=True)
media_row["country"] = grouped["country"].iloc[0] if not grouped.empty else "TUTTI"
media_row["Stagione"] = "DELTA"
media_row["Matches"] = grouped["Matches"].sum()
grouped = pd.concat([grouped, media_row.to_frame().T], ignore_index=True)

cols_pct = [col for col in grouped.columns if "_pct" in col or "AvgGoals" in col]
grouped[cols_pct] = grouped[cols_pct].round(2)

st.subheader(f"✅ League Stats Summary - {db_selected}")
st.dataframe(grouped, use_container_width=True)

# -------------------------------
# LEAGUE DATA BY START PRICE
# -------------------------------

st.subheader(f"✅ League Data by Start Price - {db_selected}")

def label_match(row):
    h = row.get("Odd home", np.nan)
    a = row.get("Odd Away", np.nan)
    if pd.isna(h) or pd.isna(a):
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

df["Label"] = df.apply(label_match, axis=1)

group_label = df.groupby("Label").agg(
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

gb = GridOptionsBuilder.from_dataframe(group_label)
gb.configure_default_column(resizable=True, filterable=True, sortable=True)
grid_options = gb.build()

AgGrid(
    group_label,
    gridOptions=grid_options,
    theme="material",
    height=400,
    fit_columns_on_grid_load=True
)

# -------------------------------
# DISTRIBUZIONE GOAL TIME FRAME
# -------------------------------

st.subheader("✅ Distribuzione Goal Time Frame (SEGNATI)")

# PREPARAZIONE DATI
# (qui sotto integra i tuoi veri minuti estratti se li hai)
# Per ora simuliamo dei dati di esempio:
# Puoi sostituire con il calcolo reale dai tuoi minuti goal se li hai già

time_bands = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90"]
labels = df["Label"].dropna().unique()

# Simuliamo DataFrame dei goal segnati
final_scored_data = []
for label in labels:
    goals = np.random.randint(0, 100, size=len(time_bands))
    total = goals.sum()
    row = {"Label": label}
    for band, g in zip(time_bands, goals):
        perc = (g/total*100) if total>0 else 0
        row[f"{band} Scored (n)"] = g
        row[f"{band} Scored (%)"] = round(perc, 2)
        row[band] = f"{g} ({round(perc,2)}%)"
    row["Total Scored"] = total
    final_scored_data.append(row)

df_scored_final = pd.DataFrame(final_scored_data)

# Visualizza AgGrid
gb = GridOptionsBuilder.from_dataframe(df_scored_final)
gb.configure_default_column(resizable=True, filterable=True, sortable=True)
gridOptions = gb.build()

AgGrid(
    df_scored_final,
    gridOptions=gridOptions,
    theme="material",
    height=400,
    fit_columns_on_grid_load=True,
)

st.subheader("✅ Distribuzione Goal Time Frame (CONCESSI)")

# Simuliamo DataFrame dei goal concessi
final_conceded_data = []
for label in labels:
    goals = np.random.randint(0, 80, size=len(time_bands))
    total = goals.sum()
    row = {"Label": label}
    for band, g in zip(time_bands, goals):
        perc = (g/total*100) if total>0 else 0
        row[f"{band} Conceded (n)"] = g
        row[f"{band} Conceded (%)"] = round(perc, 2)
        row[band] = f"{g} ({round(perc,2)}%)"
    row["Total Conceded"] = total
    final_conceded_data.append(row)

df_conceded_final = pd.DataFrame(final_conceded_data)

gb = GridOptionsBuilder.from_dataframe(df_conceded_final)
gb.configure_default_column(resizable=True, filterable=True, sortable=True)
gridOptions = gb.build()

AgGrid(
    df_conceded_final,
    gridOptions=gridOptions,
    theme="material",
    height=400,
    fit_columns_on_grid_load=True,
)
