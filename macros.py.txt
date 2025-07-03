import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import label_match, extract_minutes

def run_macro_stats(df, db_selected):
    st.title(f"Macro Stats per Campionato - {db_selected}")

    # League Stats Summary
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

    media_row = grouped.drop(columns=["country", "Stagione"]).mean(numeric_only=True)
    media_row["country"] = grouped["country"].iloc[0] if not grouped.empty else "TUTTI"
    media_row["Stagione"] = "Totale"
    media_row["Matches"] = grouped["Matches"].sum()
    grouped = pd.concat([grouped, media_row.to_frame().T], ignore_index=True)

    new_columns = {col: col.replace("_pct", " %") for col in grouped.columns if "_pct" in col}
    grouped.rename(columns=new_columns, inplace=True)

    cols_numeric = grouped.select_dtypes(include=[np.number]).columns
    grouped[cols_numeric] = grouped[cols_numeric].round(2)

    st.subheader(f"✅ League Stats Summary - {db_selected}")
    st.dataframe(
        grouped.style.format(precision=2),
        use_container_width=True
    )

    # League Data by Start Price
    df["Label"] = df.apply(label_match, axis=1)
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

    group_label.rename(columns=new_columns, inplace=True)
    group_label[cols_numeric] = group_label[cols_numeric].round(2)

    st.subheader(f"✅ League Data by Start Price - {db_selected}")
    st.dataframe(
        group_label.style.format(precision=2),
        use_container_width=True
    )

    # Plotly Goal Time Frame
    st.subheader(f"✅ Distribuzione Goal Time Frame per Label - {db_selected}")

    time_bands = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90"]

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

        scored_counts = {band: 0 for band in time_bands}
        conceded_counts = {band: 0 for band in time_bands}

        for m in minutes_scored:
            for band in time_bands:
                low, high = map(int, band.split("-"))
                if low <= m <= high:
                    scored_counts[band] += 1
                    break

        for m in minutes_conceded:
            for band in time_bands:
                low, high = map(int, band.split("-"))
                if low <= m <= high:
                    conceded_counts[band] += 1
                    break

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=time_bands,
            y=[scored_counts[b] for b in time_bands],
            name='Goals Scored',
            marker_color='green'
        ))
        fig.add_trace(go.Bar(
            x=time_bands,
            y=[conceded_counts[b] for b in time_bands],
            name='Goals Conceded',
            marker_color='red'
        ))
        fig.update_layout(
            title=f"Goal Time Frame - {label}",
            barmode='stack',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
