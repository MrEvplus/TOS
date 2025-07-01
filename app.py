import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from st_aggrid import AgGrid, GridOptionsBuilder
import datetime

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"
DATA_FILE = "serie a 20-25.xlsx"
DATA_PATH = os.path.join(DATA_FOLDER, DATA_FILE)

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

# -------------------------------
# Upload file
# -------------------------------
st.title("Serie A Trading Dashboard")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

uploaded_file = st.file_uploader("Carica il tuo database Excel:", type=["xlsx"])

if uploaded_file is not None:
    with open(DATA_PATH, "wb") as f:
        f.write(uploaded_file.read())
    st.success("✅ Database caricato e salvato con successo!")

# -------------------------------
# Caricamento file esistente
# -------------------------------
if os.path.exists(DATA_PATH):
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
else:
    st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
    st.stop()

# -------------------------------
# Filtra stagione in corso
# -------------------------------
today = datetime.datetime.today()

if "Data Partita" in df.columns:
    df["Data Partita"] = pd.to_datetime(df["Data Partita"], errors="coerce")
    
    stagione_corrente = df["Stagione"].max()

    mask_futuro = (df["Stagione"] == stagione_corrente) & (df["Data Partita"] > today)
    n_righe_futuro = mask_futuro.sum()

    if n_righe_futuro > 0:
        df = df[~mask_futuro]
        st.info(f"✅ Rimosse {n_righe_futuro} righe future dalla stagione {stagione_corrente} (partite non ancora giocate).")

# -------------------------------
# Preparazione dati base
# -------------------------------

# Calcola gol totali e per tempi
df["goals_total"] = df["Home Goal FT"] + df["Away Goal FT"]
df["goals_1st_half"] = df["Home Goal 1T"] + df["Away Goal 1T"]
df["goals_2nd_half"] = df["goals_total"] - df["goals_1st_half"]

# Esito match
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

# Arrotonda
cols_pct = [col for col in grouped.columns if "_pct" in col or "AvgGoals" in col]
grouped[cols_pct] = grouped[cols_pct].round(3)

# Calcola media per country
rows_media = []
for country in grouped["country"].unique():
    df_country = grouped[grouped["country"] == country]
    sum_matches = df_country["Matches"].sum()

    media_vals = df_country[cols_pct].multiply(df_country["Matches"], axis=0).sum()
    media_vals = media_vals / sum_matches
    media_vals = media_vals.round(3)

    media_row = {
        "country": country,
        "Stagione": "DELTA",
        "Matches": int(sum_matches)
    }
    media_row.update(media_vals.to_dict())
    rows_media.append(media_row)

media_df = pd.DataFrame(rows_media)
grouped_with_mean = pd.concat([grouped, media_df], ignore_index=True)

# -------------------------------
# Visualizza League Stats Summary
# -------------------------------

countries = sorted(df["country"].dropna().unique().tolist())
country_sel = st.selectbox("🌍 Seleziona Paese", ["Tutti"] + countries)

filtered_grouped = grouped_with_mean.copy()
if country_sel != "Tutti":
    filtered_grouped = grouped_with_mean[grouped_with_mean["country"] == country_sel]
    if filtered_grouped.empty:
        st.info("⚠ Nessun dato per il paese selezionato.")
        st.stop()

st.subheader("✅ League Stats Summary")

# Visualizzazione con AgGrid
gb = GridOptionsBuilder.from_dataframe(filtered_grouped)
gb.configure_default_column(sortable=True, filter=True, resizable=True)
gridOptions = gb.build()

AgGrid(filtered_grouped, gridOptions=gridOptions, fit_columns_on_grid_load=True)

# -------------------------------
# League Data by Start Price
# -------------------------------

st.subheader(f"✅ League Data by Start Price - {country_sel}")

# Etichetta le righe in base alle quote
def label_match(row):
    h = row["Odd home"]
    a = row["Odd Away"]
    label = ""

    if h < 1.5:
        label = "H_StrongFav <1.5"
    elif 1.5 <= h < 2:
        label = "H_MediumFav 1.5>H<2"
    elif 2 <= h < 3:
        label = "H_SmallFav 2>H<3"
    elif h <= 3 and a <= 3:
        label = "SuperCompetitive H-A<3"
    elif a < 1.5:
        label = "A_StrongFav <1.5"
    elif 1.5 <= a < 2:
        label = "A_MediumFav 1.5>A<2"
    elif 2 <= a < 3:
        label = "A_SmallFav 2>A<3"
    else:
        label = "Others"

    return label

df["Label"] = df.apply(label_match, axis=1)

if country_sel != "Tutti":
    df_label = df[df["country"] == country_sel]
else:
    df_label = df.copy()

# Calcola statistiche per label
group_label = df_label.groupby("Label").agg(
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

gb = GridOptionsBuilder.from_dataframe(group_label)
gb.configure_default_column(sortable=True, filter=True, resizable=True)
gridOptions = gb.build()

AgGrid(group_label, gridOptions=gridOptions, fit_columns_on_grid_load=True)

# -------------------------------
# Distribuzione gol segnati per fasce tempo
# -------------------------------

st.subheader(f"✅ Distribuzione gol segnati per fasce tempo - {country_sel}")

goal_minutes_home = df_label["minuti goal segnato home"].dropna().astype(str).str.split(" ")
goal_minutes_home = goal_minutes_home.explode().dropna().astype(float)

goal_minutes_away = df_label["minuti goal segnato away"].dropna().astype(str).str.split(" ")
goal_minutes_away = goal_minutes_away.explode().dropna().astype(float)

all_goal_minutes = pd.concat([goal_minutes_home, goal_minutes_away])

def classify_goal_minute(minute):
    minute = float(minute)
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

goal_bands = all_goal_minutes.apply(classify_goal_minute)

goal_band_counts = goal_bands.value_counts(normalize=True).sort_index()
goal_band_perc = (goal_band_counts * 100).to_dict()

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
    st.info(⚠️ Nessun dato sui minuti dei gol nel file caricato.")
