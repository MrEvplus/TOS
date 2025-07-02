import streamlit as st
import pandas as pd
import numpy as np
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"

st.set_page_config(page_title="Trading Dashboard", layout="wide")
st.title("Trading Dashboard")

# -------------------------------
# Upload files
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

# Lista file disponibili
db_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]
if not db_files:
    st.warning("⚠ Nessun database presente. Carica almeno un file Excel.")
    st.stop()

db_selected = st.selectbox(
    "Seleziona Campionato (Database):",
    db_files
)

DATA_PATH = os.path.join(DATA_FOLDER, db_selected)

# -------------------------------
# Caricamento Database
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
    # st.write("Colonne presenti nel database:")
    # st.write(df.columns.tolist())

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# -------------------------------
# Filtra partite già giocate
# -------------------------------
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

# -------------------------------
# Calcolo Label
# -------------------------------
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

# -------------------------------
# Fasce Tempo
# -------------------------------
time_bands = {
    "0-15": (0,15),
    "16-30": (16,30),
    "31-45": (31,45),
    "46-60": (46,60),
    "61-75": (61,75),
    "76-90": (76,120),
}

# -------------------------------
# Calcolo Distribuzione
# -------------------------------
final_scored = []
final_conceded = []

for label in df["Label"].dropna().unique():
    sub_df = df[df["Label"] == label]

    # Estrai minuti goal
    def extract_minutes(series):
        all_minutes = []
        for val in series.dropna():
            if isinstance(val, str):
                for part in val.replace(",", ";").split(";"):
                    part = part.strip()
                    if part.isdigit():
                        all_minutes.append(int(part))
        return all_minutes

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

    scored_counts = {band: 0 for band in time_bands}
    conceded_counts = {band: 0 for band in time_bands}

    for m in minutes_scored:
        for band, (low, high) in time_bands.items():
            if low <= m <= high:
                scored_counts[band] += 1
                break

    for m in minutes_conceded:
        for band, (low, high) in time_bands.items():
            if low <= m <= high:
                conceded_counts[band] += 1
                break

    total_scored = sum(scored_counts.values())
    total_conceded = sum(conceded_counts.values())

    row_scored = {"Label": label}
    row_conceded = {"Label": label}

    for band in time_bands:
        row_scored[f"{band} (n)"] = scored_counts[band]
        row_scored[f"{band} (%)"] = round((scored_counts[band] / total_scored * 100) if total_scored > 0 else 0, 2)

        row_conceded[f"{band} (n)"] = conceded_counts[band]
        row_conceded[f"{band} (%)"] = round((conceded_counts[band] / total_conceded * 100) if total_conceded > 0 else 0, 2)

    row_scored["Total Goals"] = total_scored
    row_conceded["Total Goals"] = total_conceded

    final_scored.append(row_scored)
    final_conceded.append(row_conceded)

df_scored = pd.DataFrame(final_scored)
df_conceded = pd.DataFrame(final_conceded)

# -------------------------------
# SELEZIONE COLONNE DA VISUALIZZARE
# -------------------------------

st.subheader(f"✅ Distribuzione Goal Time Frame (SEGNATI) - {db_selected}")

columns_grouped = sorted(set([c.split(" ")[0] for c in df_scored.columns if c != "Label" and c != "Total Goals"]))

bands_selected = st.multiselect(
    "Scegli intervalli di tempo da visualizzare:",
    columns_grouped,
    default=columns_grouped
)

columns_to_show = ["Label"]
for band in bands_selected:
    for suffix in ["(n)", "(%)"]:
        colname = f"{band} {suffix}"
        if colname in df_scored.columns:
            columns_to_show.append(colname)

columns_to_show.append("Total Goals")

df_compact_scored = df_scored[columns_to_show].copy()

# -------------------------------
# AGGRID SEGNATI
# -------------------------------

gb = GridOptionsBuilder.from_dataframe(df_compact_scored)
gb.configure_grid_options(domLayout='autoHeight')

for col in df_compact_scored.columns:
    gb.configure_column(col,
                        minWidth=60,
                        maxWidth=100,
                        cellStyle={'textAlign': 'center', 'fontSize': '11px', 'padding':'0px'})

js_green = JsCode("""
function(params) {
    if (params.value > 0 && params.colDef.field.includes("(%)")) {
        return {'color': 'green'};
    }
    return {};
}
""")

for col in df_compact_scored.columns:
    if "(%)" in col:
        gb.configure_column(col, cellStyle=js_green)

grid_options = gb.build()

AgGrid(
    df_compact_scored,
    gridOptions=grid_options,
    theme="material",
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=400,
)

# -------------------------------
# TABELLA CONCESSI
# -------------------------------

st.subheader(f"✅ Distribuzione Goal Time Frame (CONCESSI) - {db_selected}")

columns_to_show = ["Label"]
for band in bands_selected:
    for suffix in ["(n)", "(%)"]:
        colname = f"{band} {suffix}"
        if colname in df_conceded.columns:
            columns_to_show.append(colname)

columns_to_show.append("Total Goals")

df_compact_conceded = df_conceded[columns_to_show].copy()

gb = GridOptionsBuilder.from_dataframe(df_compact_conceded)
gb.configure_grid_options(domLayout='autoHeight')

for col in df_compact_conceded.columns:
    gb.configure_column(col,
                        minWidth=60,
                        maxWidth=100,
                        cellStyle={'textAlign': 'center', 'fontSize': '11px', 'padding':'0px'})

js_red = JsCode("""
function(params) {
    if (params.value > 0 && params.colDef.field.includes("(%)")) {
        return {'color': 'red'};
    }
    return {};
}
""")

for col in df_compact_conceded.columns:
    if "(%)" in col:
        gb.configure_column(col, cellStyle=js_red)

grid_options = gb.build()

AgGrid(
    df_compact_conceded,
    gridOptions=grid_options,
    theme="material",
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=400,
)
