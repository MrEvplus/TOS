import streamlit as st
import pandas as pd
import numpy as np
import os
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit.components.v1 import html

# -------------------------------
# Costanti
# -------------------------------
DATA_FOLDER = "data"

# Imposta titolo pagina
st.set_page_config(
    page_title="Trading Dashboard",
    layout="wide"
)

# -------------------------------
# Sidebar con navigazione
# -------------------------------
st.sidebar.title("📊 Trading Dashboard")
menu_option = st.sidebar.radio(
    "Naviga tra le sezioni:",
    [
        "Macro Stats per Campionato",
        "Statistiche per Squadre",
        "Confronto Pre Match"
    ]
)

# -------------------------------
# Sezione Upload file multipli
# -------------------------------
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

st.sidebar.header("📥 Upload Database")

uploaded_files = st.sidebar.file_uploader(
    "Carica uno o più database Excel:",
    type=["xlsx"],
    accept_multiple_files=True
)

# Salva i file caricati
if uploaded_files:
    for uploaded_file in uploaded_files:
        save_path = os.path.join(DATA_FOLDER, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
    st.sidebar.success("✅ File caricati e salvati!")

# Lista file disponibili
db_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".xlsx")]
if not db_files:
    st.warning("⚠ Nessun database presente. Carica il file Excel per iniziare.")
    st.stop()

db_selected = st.sidebar.selectbox(
    "Seleziona Campionato (Database):",
    db_files
)

DATA_PATH = os.path.join(DATA_FOLDER, db_selected)

# -------------------------------
# Caricamento file selezionato
# -------------------------------
try:
    df = pd.read_excel(DATA_PATH, sheet_name=None)
    df = list(df.values())[0]

    # Pulizia colonne
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(r"[\n\r\t]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )

    st.sidebar.success("✅ Database caricato automaticamente!")

except Exception as e:
    st.error(f"Errore nel caricamento file: {e}")
    st.stop()

# -------------------------------
# Filtro partite già giocate
# -------------------------------
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

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
# Funzione etichettatura quote
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
# Macro Stats per Campionato
# -------------------------------
if menu_option == "Macro Stats per Campionato":

    st.title(f"Macro Stats per Campionato - {db_selected}")

    # --- League Stats Summary ---
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

    # Riga Totale
    media_row = grouped.drop(columns=["country", "Stagione"]).mean(numeric_only=True)
    media_row["country"] = grouped["country"].iloc[0] if not grouped.empty else "TUTTI"
    media_row["Stagione"] = "Totale"
    media_row["Matches"] = grouped["Matches"].sum()
    grouped = pd.concat([grouped, media_row.to_frame().T], ignore_index=True)

    # Arrotonda tutto
      cols_numeric = grouped.select_dtypes(include=[np.number]).columns
      grouped[cols_numeric] = grouped[cols_numeric].round(2)

    st.subheader(f"✅ League Stats Summary - {db_selected}")
    st.dataframe(
    	grouped.style.format(precision=2),
    	use_container_width=True
)

    # --- League Data by Start Price ---
    group_label = df.groupby("Label").agg(
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

    group_label[group_label.columns[1:]] = group_label[group_label.columns[1:]].round(2)

    gb = GridOptionsBuilder.from_dataframe(group_label)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    grid_options = gb.build()

    st.subheader(f"✅ League Data by Start Price - {db_selected}")
    AgGrid(
        group_label,
        gridOptions=grid_options,
        theme="material",
        height=400,
        fit_columns_on_grid_load=True,
    )

    # -------------------------------
    # Goal Time Frame Table
    # -------------------------------
    st.subheader(f"✅ Distribuzione Goal Time Frame per Label - {db_selected}")

    time_bands = {
        "0-15": (0,15),
        "16-30": (16,30),
        "31-45": (31,45),
        "46-60": (46,60),
        "61-75": (61,75),
        "76-90": (76,120)
    }

    table_html = '<table border="1" style="border-collapse:collapse; font-size:12px; width:100%;"><thead><tr><th>Label</th>'
    for band in time_bands:
        table_html += f'<th style="text-align:center;">{band}</th>'
    table_html += '</tr></thead><tbody>'

    for label in df["Label"].dropna().unique():
        sub_df = df[df["Label"] == label]

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

        table_html += f'<tr><td>{label}</td>'

        for band in time_bands:
            sc = scored_counts[band]
            cc = conceded_counts[band]
            pct_s = round((sc/total_scored*100) if total_scored > 0 else 0,2)
            pct_c = round((cc/total_conceded*100) if total_conceded > 0 else 0,2)

            bar_html = f"""
            <div style='width:100px; height:12px; background: linear-gradient(to right, green {pct_s}%, red {pct_c}%); border-radius:3px;'></div>
            <div style='font-size:10px;'>S:{sc} ({pct_s}%)<br>C:{cc} ({pct_c}%)</div>
            """

            cell_html = f"<td style='text-align:center; padding:2px;'>{bar_html}</td>"
            table_html += cell_html

        table_html += '</tr>'

    table_html += '</tbody></table>'
    html(table_html, height=600, scrolling=True)

# -------------------------------
# Statistiche per Squadre
# -------------------------------
elif menu_option == "Statistiche per Squadre":
    st.title(f"Statistiche per Squadre - {db_selected}")
    st.info("🔧 Qui potrai implementare il calcolo di tutte le statistiche per singola squadra, sia home sia away, es. medie gol fatti/subiti, over %, etc.")

# -------------------------------
# Confronto Pre Match
# -------------------------------
elif menu_option == "Confronto Pre Match":
    st.title("Confronto Pre Match")

    squadra_casa = st.text_input("Squadra Casa")
    squadra_ospite = st.text_input("Squadra Ospite")

    col1, col2, col3 = st.columns(3)
    with col1:
        odd_home = st.number_input("Quota Vincente Casa", min_value=1.01, step=0.01)
    with col2:
        odd_draw = st.number_input("Quota Pareggio", min_value=1.01, step=0.01)
    with col3:
        odd_away = st.number_input("Quota Vincente Ospite", min_value=1.01, step=0.01)

    if squadra_casa and squadra_ospite:
        implied_home = round(100 / odd_home, 2)
        implied_draw = round(100 / odd_draw, 2)
        implied_away = round(100 / odd_away, 2)

        st.write(f"**Probabilità implicita:**")
        st.write(f"- Casa: {implied_home}%")
        st.write(f"- Pareggio: {implied_draw}%")
        st.write(f"- Ospite: {implied_away}%")

        st.info("🔧 Qui potrai implementare il confronto con le stats storiche e calcolo ROI sul range quote.")
