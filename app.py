import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

# -------------------------------
# Upload multipli
# -------------------------------
st.title("Serie A Trading Dashboard")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

uploaded_files = st.file_uploader(
    "Carica uno o più database Excel:",
    type=["xlsx"],
    accept_multiple_files=True
)

# Salva file
if uploaded_files:
    for uploaded_file in uploaded_files:
        save_path = os.path.join(DATA_FOLDER, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
    st.success("✅ File caricati e salvati!")

# Lista file
db_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]
if not db_files:
    st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
    st.stop()

db_selected = st.selectbox(
    "Seleziona Campionato (Database):",
    db_files
)

DATA_PATH = os.path.join(DATA_FOLDER, db_selected)

# -------------------------------
# Caricamento file
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
# Filtro stagione in corso
# -------------------------------
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

# -------------------------------
# Preparazione base
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
# League Stats Summary
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
# League Data by Start Price
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
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
grid_options = gb.build()

AgGrid(
    group_label,
    gridOptions=grid_options,
    theme="material",
    height=400,
    fit_columns_on_grid_load=True
)

# -------------------------------
# Tabella orizzontale Goal Time Frame con % e colori
# -------------------------------
st.subheader("✅ Distribuzione Goal Time Frame (stile Excel)")

time_bands = {
    "0-15": (0, 15),
    "16-30": (16, 30),
    "31-45": (31, 45),
    "46-60": (46, 60),
    "61-75": (61, 75),
    "76-90": (76, 120)
}

def extract_minutes(series):
    all_minutes = []
    for val in series.dropna():
        if isinstance(val, str):
            for part in val.replace(",", ";").split(";"):
                part = part.strip()
                if part.isdigit():
                    all_minutes.append(int(part))
    return all_minutes

rows = []

for label in df["Label"].dropna().unique():
    sub_df = df[df["Label"] == label]
    minutes_home = extract_minutes(sub_df["minuti goal segnato home"]) if "minuti goal segnato home" in sub_df.columns else []
    minutes_away = extract_minutes(sub_df["minuti goal segnato away"]) if "minuti goal segnato away" in sub_df.columns else []

    if label.startswith("H_"):
        minutes_scored = minutes_home
        minutes_conceded = minutes_away
    elif label.startswith("A_"):
        minutes_scored = minutes_away
        minutes_conceded = minutes_home
    else:
        minutes_scored = minutes_home + minutes_away
        minutes_conceded = []

    scored_counts = {}
    conceded_counts = {}

    for band, (low, high) in time_bands.items():
        goals_scored = sum(1 for m in minutes_scored if low <= m <= high)
        goals_conceded = sum(1 for m in minutes_conceded if low <= m <= high)
        scored_counts[band] = goals_scored
        conceded_counts[band] = goals_conceded

    total_scored = sum(scored_counts.values())
    total_conceded = sum(conceded_counts.values())

    scored_perc = {
        band: round((scored_counts[band]/total_scored * 100), 2) if total_scored > 0 else 0.00
        for band in time_bands
    }
    conceded_perc = {
        band: round((conceded_counts[band]/total_conceded * 100), 2) if total_conceded > 0 else 0.00
        for band in time_bands
    }

    row = {"Label": label}
    for band in time_bands:
        row[f"{band} Scored (n)"] = scored_counts[band]
        row[f"{band} Scored (%)"] = scored_perc[band]
        row[f"{band} Conceded (n)"] = conceded_counts[band]
        row[f"{band} Conceded (%)"] = conceded_perc[band]

    row["Total Scored"] = total_scored
    row["Total Conceded"] = total_conceded
    rows.append(row)

if rows:
    df_final = pd.DataFrame(rows)

    # Ordine colonne
    columns_ordered = ["Label"]
    for band in time_bands:
        columns_ordered.append(f"{band} Scored (n)")
        columns_ordered.append(f"{band} Scored (%)")
        columns_ordered.append(f"{band} Conceded (n)")
        columns_ordered.append(f"{band} Conceded (%)")
    columns_ordered += ["Total Scored", "Total Conceded"]
    df_final = df_final[columns_ordered]

    # Costruisci AgGrid con colori
    gb = GridOptionsBuilder.from_dataframe(df_final)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)

    # Colorazione dinamica
    for col in df_final.columns:
        if "Scored (%)" in col:
            gb.configure_column(
                col,
                cellStyle=lambda params: {
                    "backgroundColor": f"rgba(0, 200, 0, {params.value/100})" if params.value > 0 else "",
                    "color": "black"
                }
            )
        elif "Conceded (%)" in col:
            gb.configure_column(
                col,
                cellStyle=lambda params: {
                    "backgroundColor": f"rgba(255, 0, 0, {params.value/100})" if params.value > 0 else "",
                    "color": "black"
                }
            )

    grid_options = gb.build()

    AgGrid(
        df_final,
        gridOptions=grid_options,
        theme="material",
        height=600,
        fit_columns_on_grid_load=True
    )
else:
    st.info("⚠ Nessun dato sui minuti dei goal nel file caricato.")
