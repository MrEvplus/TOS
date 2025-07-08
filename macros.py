import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import label_match, extract_minutes

def calculate_goal_timeframes(sub_df, label):
    """
    Calcola la distribuzione % dei goal segnati e concessi per intervallo di minuti.
    """

    time_bands = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90"]

    # Tenta di leggere colonne minuti goal segnato
    minutes_home = extract_minutes(sub_df["minuti goal segnato home"]) if "minuti goal segnato home" in sub_df.columns else []
    minutes_away = extract_minutes(sub_df["minuti goal segnato away"]) if "minuti goal segnato away" in sub_df.columns else []

    # Fallback su gh1…9 e ga1…9 se mancano i minuti
    if len(minutes_home) == 0:
        minutes_home = []
        for col in ["gh1","gh2","gh3","gh4","gh5","gh6","gh7","gh8","gh9"]:
            if col in sub_df.columns:
                val = sub_df[col].values[0]
                if not pd.isna(val) and val != 0:
                    minutes_home.append(int(val))

    if len(minutes_away) == 0:
        minutes_away = []
        for col in ["ga1","ga2","ga3","ga4","ga5","ga6","ga7","ga8","ga9"]:
            if col in sub_df.columns:
                val = sub_df[col].values[0]
                if not pd.isna(val) and val != 0:
                    minutes_away.append(int(val))

    # Determina se home o away
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
    for m in minutes_scored:
        for band in time_bands:
            low, high = map(int, band.split("-"))
            if low <= m <= high:
                scored_counts[band] += 1
                break

    conceded_counts = {band: 0 for band in time_bands}
    for m in minutes_conceded:
        for band in time_bands:
            low, high = map(int, band.split("-"))
            if low <= m <= high:
                conceded_counts[band] += 1
                break

    total_scored = sum(scored_counts.values())
    total_conceded = sum(conceded_counts.values())

    scored_percents = {
        band: round((scored_counts[band] / total_scored * 100), 2) if total_scored > 0 else 0
        for band in time_bands
    }

    conceded_percents = {
        band: round((conceded_counts[band] / total_conceded * 100), 2) if total_conceded > 0 else 0
        for band in time_bands
    }

    return scored_percents, conceded_percents

# --------------------------------------------------------
# MAIN FUNCTION
# --------------------------------------------------------

def run_macro_stats(df, db_selected):
    st.title(f"Macro Stats per Campionato - {db_selected}")

    if df.empty:
        st.warning("⚠️ Il file caricato è vuoto o non contiene righe.")
        st.stop()

    required_cols = [
        "Home", "Away",
        "Home Goal FT", "Away Goal FT",
        "Home Goal 1T", "Away Goal 1T",
        "country", "Stagione"
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"⚠️ Mancano colonne essenziali nel database: {missing_cols}")
        st.write("Colonne presenti nel file:", list(df.columns))
        st.stop()

    df["country"] = df["country"].fillna("Unknown").astype(str).replace("", "Unknown")
    df["Stagione"] = df["Stagione"].fillna("Unknown").astype(str).replace("", "Unknown")

    if "goals_total" not in df.columns:
        df["goals_total"] = df["Home Goal FT"] + df["Away Goal FT"]

    if "goals_1st_half" not in df.columns:
        df["goals_1st_half"] = df["Home Goal 1T"] + df["Away Goal 1T"]

    if "goals_2nd_half" not in df.columns:
        df["goals_2nd_half"] = df["goals_total"] - df["goals_1st_half"]

    if "btts" not in df.columns:
        df["btts"] = ((df["Home Goal FT"] > 0) & (df["Away Goal FT"] > 0)).astype(int)

    if "match_result" not in df.columns:
        df["match_result"] = df.apply(
            lambda row: (
                "Home Win" if row["Home Goal FT"] > row["Away Goal FT"]
                else "Away Win" if row["Home Goal FT"] < row["Away Goal FT"]
                else "Draw"
            ),
            axis=1
        )

    home_col = "Home"

    group_cols = ["country", "Stagione"]
    grouped = df.groupby(group_cols).agg(
        Matches=(home_col, "count"),
        HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean() * 100),
        Draw_pct=("match_result", lambda x: (x == "Draw").mean() * 100),
        AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean() * 100),
        AvgGoals1T=("goals_1st_half", "mean"),
        AvgGoals2T=("goals_2nd_half", "mean"),
        AvgGoalsTotal=("goals_total", "mean"),
        Over05_FH_pct=("goals_1st_half", lambda x: (x > 0.5).mean() * 100),
        Over15_FH_pct=("goals_1st_half", lambda x: (x > 1.5).mean() * 100),
        Over25_FH_pct=("goals_1st_half", lambda x: (x > 2.5).mean() * 100),
        Over05_FT_pct=("goals_total", lambda x: (x > 0.5).mean() * 100),
        Over15_FT_pct=("goals_total", lambda x: (x > 1.5).mean() * 100),
        Over25_FT_pct=("goals_total", lambda x: (x > 2.5).mean() * 100),
        Over35_FT_pct=("goals_total", lambda x: (x > 3.5).mean() * 100),
        Over45_FT_pct=("goals_total", lambda x: (x > 4.5).mean() * 100),
        BTTS_pct=("btts", lambda x: x.mean() * 100),
    ).reset_index()

    new_columns = {}
    for col in grouped.columns:
        if "pct" in col:
            new_col = col.replace("_pct", " %").replace("pct", "%")
        else:
            new_col = col
        new_columns[col] = new_col

    grouped.rename(columns=new_columns, inplace=True)
    cols_numeric = grouped.select_dtypes(include=[np.number]).columns
    grouped[cols_numeric] = grouped[cols_numeric].round(2)

    st.subheader(f"✅ League Stats Summary - {db_selected}")
    st.dataframe(grouped, use_container_width=True, hide_index=True)

    # League Data by Start Price
    df["Label"] = df.apply(label_match, axis=1)
    group_label = df.groupby("Label").agg(
        Matches=(home_col, "count"),
        HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean() * 100),
        Draw_pct=("match_result", lambda x: (x == "Draw").mean() * 100),
        AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean() * 100),
        AvgGoals1T=("goals_1st_half", "mean"),
        AvgGoals2T=("goals_2nd_half", "mean"),
        AvgGoalsTotal=("goals_total", "mean"),
        Over05_FH_pct=("goals_1st_half", lambda x: (x > 0.5).mean() * 100),
        Over15_FH_pct=("goals_1st_half", lambda x: (x > 1.5).mean() * 100),
        Over25_FH_pct=("goals_1st_half", lambda x: (x > 2.5).mean() * 100),
        Over05_FT_pct=("goals_total", lambda x: (x > 0.5).mean() * 100),
        Over15_FT_pct=("goals_total", lambda x: (x > 1.5).mean() * 100),
        Over25_FT_pct=("goals_total", lambda x: (x > 2.5).mean() * 100),
        Over35_FT_pct=("goals_total", lambda x: (x > 3.5).mean() * 100),
        Over45_FT_pct=("goals_total", lambda x: (x > 4.5).mean() * 100),
        BTTS_pct=("btts", lambda x: x.mean() * 100),
    ).reset_index()

    group_label.rename(columns=new_columns, inplace=True)
    group_label[cols_numeric] = group_label[cols_numeric].round(2)

    st.subheader(f"✅ League Data by Start Price - {db_selected}")
    st.dataframe(group_label, use_container_width=True, hide_index=True)

    # Goal time frame plots
    st.subheader(f"✅ Distribuzione Goal Time Frame % per Label - {db_selected}")

    labels = list(df["Label"].dropna().unique())

    for i in range(0, len(labels), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(labels):
                label = labels[i + j]
                sub_df = df[df["Label"] == label]
                scored_percents, conceded_percents = calculate_goal_timeframes(sub_df, label)

                time_bands = list(scored_percents.keys())

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=time_bands,
                    y=[scored_percents[b] for b in time_bands],
                    name='Goals Scored (%)',
                    marker_color='green'
                ))

                fig.add_trace(go.Bar(
                    x=time_bands,
                    y=[conceded_percents[b] for b in time_bands],
                    name='Goals Conceded (%)',
                    marker_color='red'
                ))

                fig.update_layout(
                    title=f"Goal Time Frame % - {label}",
                    barmode='group',
                    height=400,
                    yaxis=dict(title='Percentage (%)')
                )

                with cols[j]:
                    st.plotly_chart(fig, use_container_width=True)
