import streamlit as st
import pandas as pd
import numpy as np
import os
import datetime
from st_aggrid import AgGrid, GridOptionsBuilder

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

# -------------------------------
# Sezione Upload file
# -------------------------------
st.title("Serie A Trading Dashboard")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

uploaded_file = st.file_uploader("Carica uno o più database Excel:", type=["xlsx"], accept_multiple_files=True)

if uploaded_file:
    for up in uploaded_file:
        save_path = os.path.join(DATA_FOLDER, up.name)
        with open(save_path, "wb") as f:
            f.write(up.read())
    st.success("✅ File caricati e salvati!")

# -------------------------------
# Selezione file da lista
# -------------------------------
files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]
if not files:
    st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
    st.stop()

selected_file = st.selectbox("📂 Seleziona Campionato (Database):", files)
DATA_PATH = os.path.join(DATA_FOLDER, selected_file)

# -------------------------------
# Caricamento file Excel
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
# Filtro solo partite già giocate
# -------------------------------
oggi = datetime.datetime.now()

if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    df_filtered = df[df["Data"] <= oggi]
else:
    df_filtered = df.copy()

# -------------------------------
# Preparazione dati
# -------------------------------
df_filtered["goals_total"] = df_filtered["Home Goal FT"] + df_filtered["Away Goal FT"]
df_filtered["goals_1st_half"] = df_filtered["Home Goal 1T"] + df_filtered["Away Goal 1T"]
df_filtered["goals_2nd_half"] = df_filtered["goals_total"] - df_filtered["goals_1st_half"]

df_filtered["match_result"] = np.select(
    [
        df_filtered["Home Goal FT"] > df_filtered["Away Goal FT"],
        df_filtered["Home Goal FT"] == df_filtered["Away Goal FT"],
        df_filtered["Home Goal FT"] < df_filtered["Away Goal FT"]
    ],
    ["Home Win", "Draw", "Away Win"],
    default="Unknown"
)

df_filtered["btts"] = np.where(
    (df_filtered["Home Goal FT"] > 0) & (df_filtered["Away Goal FT"] > 0),
    1, 0
)

# -------------------------------
# League Stats Summary
# -------------------------------
group_cols = ["country", "Stagione"]

grouped = df_filtered.groupby(group_cols).agg(
    Matches=("Home Goal FT", "count"),
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

# Media su tutte le stagioni filtrate
if not grouped.empty:
    media = grouped.drop(columns=["country", "Stagione"]).mean().to_frame().T
    media["country"] = grouped["country"].iloc[0]
    media["Stagione"] = "DELTA"
    media["Matches"] = grouped["Matches"].sum()
    grouped = pd.concat([grouped, media], ignore_index=True)

cols_pct = [col for col in grouped.columns if "_pct" in col or "AvgGoals" in col]
grouped[cols_pct] = grouped[cols_pct].round(2)

st.subheader("✅ League Stats Summary")
gb = GridOptionsBuilder.from_dataframe(grouped)
gb.configure_default_column(sortable=True, filter=True)
grid_options = gb.build()
AgGrid(grouped, gridOptions=grid_options, theme='material', height=350, width='100%')

# -------------------------------
# Distribuzione gol segnati per fasce tempo
# -------------------------------

goal_cols_home = ["BW", "BX", "BY", "BZ", "CA", "CB", "CC", "CD", "CE", "CF"]
goal_cols_away = ["CG", "CH", "CI", "CJ", "CK", "CL", "CM", "CN", "CO", "CP"]

def extract_from_series(series):
    minuti = []
    for val in series.dropna():
        if isinstance(val, (int, float)):
            minuti.append(int(val))
        else:
            split_vals = str(val).split(";")
            for item in split_vals:
                item = item.strip()
                if item.isdigit():
                    minuti.append(int(item))
    return minuti

minuti_home = []
for col in goal_cols_home:
    if col in df_filtered.columns:
        minuti_home.extend(extract_from_series(df_filtered[col]))

minuti_away = []
for col in goal_cols_away:
    if col in df_filtered.columns:
        minuti_away.extend(extract_from_series(df_filtered[col]))

all_minutes = minuti_home + minuti_away

def classify_goal_minute(minute):
    if minute <= 15:
        return "0-15"
    elif minute <= 30:
        return "16-30"
    elif minute <= 45:
        return "31-45"
    elif minute <= 60:
        return "46-60"
    elif minute <= 75:
        return "61-75"
    else:
        return "76-90"

if all_minutes:
    bands = pd.Series([classify_goal_minute(m) for m in all_minutes])
    band_counts = bands.value_counts(normalize=True).sort_index()
    band_perc = (band_counts * 100).round(2)

    band_chart = pd.DataFrame({
        "Time Band": band_perc.index,
        "Percentage": band_perc.values
    })

    st.subheader(f"📊 Distribuzione gol segnati per fasce tempo - {selected_file}")
    fig = px.bar(
        band_chart,
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

# Etichetta le righe in base alle quote
def label_match(row):
    h = row.get("Odd home", np.nan)
    a = row.get("Odd Away", np.nan)

    label = "Others"
    try:
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
    except:
        pass

    return label

if "Odd home" in df_filtered.columns and "Odd Away" in df_filtered.columns:
    df_filtered["Label"] = df_filtered.apply(label_match, axis=1)

    group_label = df_filtered.groupby("Label").agg(
        Matches=("Home Goal FT", "count"),
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

    st.subheader(f"✅ League Data by Start Price - {selected_file}")
    gb = GridOptionsBuilder.from_dataframe(group_label)
    gb.configure_default_column(sortable=True, filter=True)
    grid_options_label = gb.build()
    AgGrid(group_label, gridOptions=grid_options_label, theme='material', height=350, width='100%')
else:
    st.warning("⚠ Il file non contiene le colonne 'Odd home' e 'Odd Away'.")
