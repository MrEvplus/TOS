import streamlit as st
import pandas as pd
import numpy as np
import os

DATA_FOLDER = "data"
DATA_FILE = "serie a 20-25.xlsx"
DATA_PATH = os.path.join(DATA_FOLDER, DATA_FILE)

st.set_page_config(page_title="Serie A Trading Dashboard", layout="wide")

st.title("Serie A Trading Dashboard")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

uploaded_file = st.file_uploader("Carica il tuo database Excel:", type=["xlsx"])

if uploaded_file is not None:
    with open(DATA_PATH, "wb") as f:
        f.write(uploaded_file.read())
    st.success("✅ Database caricato e salvato con successo!")

if os.path.exists(DATA_PATH):
    df = pd.read_excel(DATA_PATH, sheet_name=None)
    df = list(df.values())[0]
else:
    st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
    st.stop()

# calcola goal totali e per tempi
df["goals_total"] = df["Home Goal FT"] + df["Away Goal FT"]
df["goals_1st_half"] = df["Home Goal 1T"] + df["Away Goal 1T"]
df["goals_2nd_half"] = df["goals_total"] - df["goals_1st_half"]

# esito match
df["match_result"] = np.select(
    [
        df["Home Goal FT"] > df["Away Goal FT"],
        df["Home Goal FT"] == df["Away Goal FT"],
        df["Home Goal FT"] < df["Away Goal FT"],
    ],
    ["Home Win", "Draw", "Away Win"],
)

# btts
df["btts"] = np.where(
    (df["Home Goal FT"] > 0) & (df["Away Goal FT"] > 0),
    1,
    0
)

# definisci label odds
def label_match(row):
    h = row.get("Odd home", np.nan)
    a = row.get("Odd Away", np.nan)

    if pd.isna(h) or pd.isna(a):
        return "Unknown"

    if h < 1.5:
        return "H_StrongFav"
    elif 1.5 <= h < 2.0:
        return "H_MediumFav"
    elif 2.0 <= h < 3.0:
        return "H_SmallFav"
    elif h < 3.0 and a < 3.0:
        return "SuperCompetitive"
    elif 2.0 <= a < 3.0:
        return "A_SmallFav"
    elif 1.5 <= a < 2.0:
        return "A_MediumFav"
    elif a < 1.5:
        return "A_StrongFav"
    else:
        return "Other"

df["Label"] = df.apply(label_match, axis=1)

# calcola goal bands
goal_cols_home = [
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
    "1  goal away (min)",
    "2  goal away (min)",
    "3 goal away (min)",
    "4  goal away (min)",
    "5  goal away (min)",
    "6  goal away (min)",
    "7  goal away (min)",
    "8  goal away (min)",
    "9  goal away (min)",
]

goal_bands = ["0-15", "16-30", "31-45", "46-60", "60-75", "76-90"]

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

# calcola goal bands per ciascuna partita
goal_band_counts = []

for i, row in df.iterrows():
    all_minutes = []
    for col in goal_cols_home + goal_cols_away:
        if col in df.columns:
            minute = row.get(col)
            if not pd.isna(minute):
                band = classify_goal_minute(minute)
                all_minutes.append(band)
    # converti in set per sapere in quali bande ci sono stati goal
    all_bands = set([b for b in all_minutes if b is not None])
    goal_band_counts.append(all_bands)

df["goal_bands_set"] = goal_band_counts

# calcola First to Score
def first_scorer(row):
    home_min = None
    away_min = None

    for col in goal_cols_home:
        if col in df.columns and not pd.isna(row.get(col)):
            home_min = row[col]
            break

    for col in goal_cols_away:
        if col in df.columns and not pd.isna(row.get(col)):
            away_min = row[col]
            break

    if home_min is None and away_min is None:
        return "None"
    elif home_min is None:
        return "Away"
    elif away_min is None:
        return "Home"
    else:
        return "Home" if home_min < away_min else "Away"

df["FirstScorer"] = df.apply(first_scorer, axis=1)

# aggregazione
result = []

for label, grp in df.groupby("Label"):
    d = {}
    d["Label"] = label

    # odds range
    odds_map = {
        "H_StrongFav": "[H<1.5]",
        "H_MediumFav": "[1.5≤H<2]",
        "H_SmallFav": "[2≤H<3]",
        "SuperCompetitive": "[H<3∧A<3]",
        "A_SmallFav": "[2≤A<3]",
        "A_MediumFav": "[1.5≤A<2]",
        "A_StrongFav": "[A<1.5]",
    }
    d["Odds"] = odds_map.get(label, "-")

    d["Matches"] = len(grp)
    d["home"] = round((grp["match_result"] == "Home Win").mean() * 100, 2)
    d["draw"] = round((grp["match_result"] == "Draw").mean() * 100, 2)
    d["away"] = round((grp["match_result"] == "Away Win").mean() * 100, 2)

    d["1st Half"] = round(grp["goals_1st_half"].mean(), 2)
    d["2nd Half"] = round(grp["goals_2nd_half"].mean(), 2)
    d["total"] = round(grp["goals_total"].mean(), 2)

    for ov in [0.5, 1.5, 2.5]:
        d[f"Over {ov} FH"] = round((grp["goals_1st_half"] > ov).mean() * 100, 2)

    for ov in [0.5, 1.5, 2.5, 3.5, 4.5]:
        d[f"Over {ov} FT"] = round((grp["goals_total"] > ov).mean() * 100, 2)

    d["bts"] = round(grp["btts"].mean() * 100, 2)

    # goal bands
    for band in goal_bands:
        d[band] = round(
            grp["goal_bands_set"].apply(lambda s: band in s if isinstance(s, set) else False).mean() * 100, 2
        )

    # First scorer
    d["Home"] = round((grp["FirstScorer"] == "Home").mean() * 100, 2)
    d["H Win"] = round(
        ((grp["FirstScorer"] == "Home") & (grp["match_result"] == "Home Win")).mean() * 100, 2
    )
    d["Away"] = round((grp["FirstScorer"] == "Away").mean() * 100, 2)
    d["A Win"] = round(
        ((grp["FirstScorer"] == "Away") & (grp["match_result"] == "Away Win")).mean() * 100, 2
    )

    result.append(d)

final = pd.DataFrame(result)

st.subheader("League Data by Start Price")

st.dataframe(final, use_container_width=True)
