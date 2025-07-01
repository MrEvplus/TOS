import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

st.set_page_config(page_title="Football Trading Dashboard", layout="wide")

st.title("⚽ Football Trading Dashboard (Multi-League)")

# -------------------------------
# Upload multipli file Excel
# -------------------------------
uploaded_files = st.file_uploader(
    "Carica uno o più file Excel (uno per campionato)",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        save_path = os.path.join(DATA_FOLDER, file.name)
        with open(save_path, "wb") as f:
            f.write(file.read())
    st.success("✅ File caricati con successo!")

# -------------------------------
# Elenco file disponibili
# -------------------------------
files = [
    f for f in os.listdir(DATA_FOLDER)
    if f.lower().endswith(".xlsx")
]

if not files:
    st.warning("⚠ Nessun database presente. Carica almeno un file Excel.")
    st.stop()

# -------------------------------
# Selectbox campionati disponibili
# -------------------------------
selected_file = st.selectbox(
    "Seleziona il campionato da analizzare:",
    files,
    format_func=lambda x: x.replace(".xlsx", "").replace("_", " ").title()
)

# -------------------------------
# Caricamento DataFrame selezionato
# -------------------------------
DATA_PATH = os.path.join(DATA_FOLDER, selected_file)
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
    st.success(f"✅ Database caricato: {selected_file}")
except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# -------------------------------
# Preparazione dati base
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
# Funzioni per Goal Bands
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

def compute_goal_band(sub_df, goal_cols):
    minutes = []
    for col in goal_cols:
        if col in sub_df.columns:
            minutes.extend(sub_df[col].dropna().apply(classify_goal_minute).values)
    if len(minutes) == 0:
        return {}
    band_counts = pd.Series(minutes).value_counts(normalize=True).sort_index()
    return (band_counts * 100).round(2).to_dict(), len(minutes)

# -------------------------------
# League Stats Summary
# -------------------------------

grouped = df.groupby(["country", "Stagione"]).agg(
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

cols_pct = [col for col in grouped.columns if "_pct" in col or "AvgGoals" in col]
grouped[cols_pct] = grouped[cols_pct].round(2)

# Totale/Media
total_row = pd.DataFrame(grouped.iloc[:, 2:].mean()).T
total_row.insert(0, "Stagione", "TUTTI")
total_row.insert(0, "country", "MEDIA")
grouped = pd.concat([grouped, total_row], ignore_index=True)

st.subheader("✅ League Stats Summary")
st.dataframe(grouped, use_container_width=True)

# -------------------------------
# Distribuzione globale goal bands
# -------------------------------
goal_band_counts, total_goals = compute_goal_band(df, goal_cols_home + goal_cols_away)

goal_band_df = pd.DataFrame({
    "Time Band": list(goal_band_counts.keys()),
    "Percentage": list(goal_band_counts.values())
})

st.subheader(f"Distribuzione gol per fasce tempo - {selected_file}")
if not goal_band_df.empty:
    fig = px.bar(
        goal_band_df,
        x="Time Band",
        y="Percentage",
        text="Percentage",
        color="Time Band",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessun dato disponibile.")

# -------------------------------
# League Data by Start Price
# -------------------------------

st.subheader("✅ League Data by Start Price")

def label_match(row):
    h = row["Odd home"]
    a = row["Odd Away"]
    if h < 1.5:
        return "H_StrongFav"
    elif 1.5 <= h < 2:
        return "H_MediumFav"
    elif 2 <= h < 3:
        return "H_SmallFav"
    elif h <= 3 and a <= 3:
        return "SuperCompetitive"
    elif a < 1.5:
        return "A_StrongFav"
    elif 1.5 <= a < 2:
        return "A_MediumFav"
    elif 2 <= a < 3:
        return "A_SmallFav"
    else:
        return "Others"

df["Label"] = df.apply(label_match, axis=1)

records = []
goal_bands = ["0-15", "16-30", "31-45", "46-60", "60-75", "76-90"]

for label in df["Label"].unique():
    sub_df = df[df["Label"] == label]

    goals_scored, goals_scored_total = compute_goal_band(sub_df, goal_cols_home)
    goals_conceded, goals_conceded_total = compute_goal_band(sub_df, goal_cols_away)

    record = {
        "Label": label,
        "Matches": len(sub_df),
        "Goals Scored Total": goals_scored_total,
        "Goals Conceded Total": goals_conceded_total
    }

    for band in goal_bands:
        record[f"GS {band} %"] = goals_scored.get(band, 0.0)
        record[f"GC {band} %"] = goals_conceded.get(band, 0.0)

    records.append(record)

df_aggrid = pd.DataFrame(records)
gb = GridOptionsBuilder.from_dataframe(df_aggrid)
gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
gridOptions = gb.build()

AgGrid(
    df_aggrid,
    gridOptions=gridOptions,
    height=500,
    theme="alpine"
)

# -------------------------------
# Grafici per ciascuna Label
# -------------------------------
st.subheader("Grafici goal segnati e subiti per Label")

for label in df["Label"].unique():
    sub_df = df[df["Label"] == label]
    gs, _ = compute_goal_band(sub_df, goal_cols_home)
    gc, _ = compute_goal_band(sub_df, goal_cols_away)

    st.markdown(f"### 🔹 {label}")

    if gs:
        st.plotly_chart(
            px.bar(
                pd.DataFrame({"Time Band": list(gs.keys()), "Goals %": list(gs.values())}),
                x="Time Band", y="Goals %", text="Goals %",
                color="Time Band"
            ), use_container_width=True
        )
    if gc:
        st.plotly_chart(
            px.bar(
                pd.DataFrame({"Time Band": list(gc.keys()), "Goals %": list(gc.values())}),
                x="Time Band", y="Goals %", text="Goals %",
                color="Time Band"
            ), use_container_width=True
        )

