import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

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
# Caricamento automatico file esistente
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
# Dropdown selezione campionato
# -------------------------------
countries = sorted(df["country"].dropna().unique().tolist())
country_sel = st.selectbox("🌍 Seleziona Campionato", countries)

# Filtra il dataframe
df_filtered = df[df["country"] == country_sel]

# -------------------------------
# CALCOLO GOAL BANDS sul campionato filtrato
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

goal_minutes = []
for col in goal_cols_home + goal_cols_away:
    if col in df_filtered.columns:
        goal_minutes.extend(
            df_filtered[col].dropna().apply(classify_goal_minute).values
        )

goal_band_counts = pd.Series(goal_minutes).value_counts(normalize=True).sort_index()
goal_band_perc = (goal_band_counts * 100).to_dict()

# -------------------------------
# League Stats Summary (campionato filtrato)
# -------------------------------

grouped = df_filtered.groupby(["country", "Stagione"]).agg(
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

st.subheader(f"League Stats Summary - {country_sel}")
st.dataframe(grouped, use_container_width=True)

# -------------------------------
# Visualizza GRAFICO GOAL BANDS
# -------------------------------

st.subheader(f"Distribuzione gol per fasce tempo - {country_sel}")

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
    st.info("Non ci sono dati sui minuti dei goal nel file caricato.")

# -------------------------------
# League Data by Start Price
# -------------------------------

st.subheader(f"League Data by Start Price - {country_sel}")

# Etichetta le righe in base alle quote
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
    elif h < 3 and a < 3:
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

# Aggiungo colonne "First To Score" dummy
group_label["FirstToScore_Home"] = 0
group_label["FirstToScore_HWin"] = 0
group_label["FirstToScore_Away"] = 0
group_label["FirstToScore_AWin"] = 0

# -------------------------------
# CREAZIONE TABELLA MULTI-HEADER HTML
# -------------------------------

# Costruisci intestazioni multi-riga
top_header = [
    "League", 
    "Match Result", "Match Result", "Match Result",
    "Average Goals", "Average Goals", "Average Goals",
    "First Half Overs", "First Half Overs", "First Half Overs",
    "Full Match Overs", "Full Match Overs", "Full Match Overs",
    "Goal Bands",
    "First To Score %", "First To Score %", "First To Score %", "First To Score %"
]

sub_header = [
    "Label", 
    "home", "draw", "away",
    "1st Half", "2nd Half", "total",
    "0.5 FH", "1.5 FH", "2.5 FH",
    "0.5 FT", "1.5 FT", "2.5 FT",
    "bts",
    "Home", "H Win", "Away", "A Win"
]

multi_cols = pd.MultiIndex.from_tuples(zip(top_header, sub_header))

# Colonne da mostrare
final_cols = [
    "Label", 
    "HomeWin_pct", "Draw_pct", "AwayWin_pct",
    "AvgGoals1T", "AvgGoals2T", "AvgGoalsTotal",
    "Over0_5_FH_pct", "Over1_5_FH_pct", "Over2_5_FH_pct",
    "Over0_5_FT_pct", "Over1_5_FT_pct", "Over2_5_FT_pct",
    "BTTS_pct",
    "FirstToScore_Home", "FirstToScore_HWin", "FirstToScore_Away", "FirstToScore_AWin"
]

df_html = group_label[final_cols].copy()
df_html.columns = multi_cols

html_table = df_html.to_html(
    escape=False,
    index=False,
    border=1,
    classes='dataframe table table-striped table-bordered'
)

st.markdown("## ✅ League Data by Start Price (Versione HTML - stile Screenshot)")
st.markdown(html_table, unsafe_allow_html=True)

