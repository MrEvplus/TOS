import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import extract_minutes

def run_team_stats(df, db_selected):
    st.header("📊 Statistiche per Squadre")

    # Normalizza country e db_selected
    df["country"] = df["country"].fillna("").astype(str).str.strip().str.upper()
    db_selected = db_selected.strip().upper()

    if db_selected not in df["country"].unique():
        st.warning(f"⚠️ Il campionato selezionato '{db_selected}' non è presente nel database.")
        st.stop()

    df_filtered = df[df["country"] == db_selected]

    seasons_available = sorted(df_filtered["Stagione"].dropna().unique().tolist(), reverse=True)

    if not seasons_available:
        st.warning(f"⚠️ Nessuna stagione disponibile nel database per il campionato {db_selected}.")
        st.stop()

    st.write(f"Stagioni disponibili nel database: {seasons_available}")

    seasons_selected = st.multiselect(
        "Seleziona le stagioni su cui vuoi calcolare le statistiche:",
        options=seasons_available,
        default=seasons_available[:1]
    )

    if not seasons_selected:
        st.warning("Seleziona almeno una stagione.")
        st.stop()

    df_filtered = df_filtered[df_filtered["Stagione"].isin(seasons_selected)]

    teams_available = sorted(set(df_filtered["Home"].dropna().unique()) | set(df_filtered["Away"].dropna().unique()))
    
    col1, col2 = st.columns(2)

    with col1:
        team_1 = st.selectbox("Seleziona Squadra 1", options=teams_available)

    with col2:
        team_2 = st.selectbox(
            "Seleziona Squadra 2 (facoltativa - per confronto)",
            options=[""] + teams_available
        )

    if team_1:
        st.subheader(f"✅ Statistiche Macro per {team_1}")
        show_team_macro_stats(df_filtered, team_1)

    if team_2 and team_2 != team_1:
        st.subheader(f"✅ Statistiche Macro per {team_2}")
        show_team_macro_stats(df_filtered, team_2)

        st.subheader(f"⚔️ Goal Patterns - {team_1} vs {team_2}")
        show_goal_patterns(df_filtered, team_1, team_2)


def show_team_macro_stats(df, team):
    df_home = df[df["Home"] == team]
    df_away = df[df["Away"] == team]

    stats = []

    for venue, data in [("Home", df_home), ("Away", df_away)]:
        total_matches = len(data)

        if total_matches > 0:
            home_wins = sum(data["Home Goal FT"] > data["Away Goal FT"]) if venue == "Home" else sum(data["Away Goal FT"] > data["Home Goal FT"])
            draws = sum(data["Home Goal FT"] == data["Away Goal FT"])
            away_wins = sum(data["Away Goal FT"] > data["Home Goal FT"]) if venue == "Home" else sum(data["Home Goal FT"] > data["Away Goal FT"])

            goals_for = data["Home Goal FT"].mean() if venue == "Home" else data["Away Goal FT"].mean()
            goals_against = data["Away Goal FT"].mean() if venue == "Home" else data["Home Goal FT"].mean()

            if "gg" in data.columns:
                btts = data["gg"].mean() * 100
            else:
                btts = None

            stats.append({
                "Venue": venue,
                "Matches": total_matches,
                "Win %": round((home_wins / total_matches) * 100, 2),
                "Draw %": round((draws / total_matches) * 100, 2),
                "Loss %": round((away_wins / total_matches) * 100, 2),
                "Avg Goals Scored": round(goals_for, 2),
                "Avg Goals Conceded": round(goals_against, 2),
                "BTTS %": round(btts, 2) if btts is not None else None
            })

    if stats:
        df_stats = pd.DataFrame(stats)
        st.dataframe(df_stats, use_container_width=True)
    else:
        st.info("⚠️ Nessuna partita trovata per la squadra selezionata.")


def show_goal_patterns(df, team1, team2):
    matches = df[
        ((df["Home"] == team1) & (df["Away"] == team2)) |
        ((df["Home"] == team2) & (df["Away"] == team1))
    ]

    if matches.empty:
        st.info("⚠️ Nessuna partita disponibile tra le due squadre selezionate.")
        return

    total_matches = len(matches)

    def pct(count):
        return round((count / total_matches) * 100, 2) if total_matches > 0 else 0

    # Calcola Goal Patterns
    # H, D, A
    home_wins = sum(matches["Home Goal FT"] > matches["Away Goal FT"])
    draws = sum(matches["Home Goal FT"] == matches["Away Goal FT"])
    away_wins = sum(matches["Home Goal FT"] < matches["Away Goal FT"])

    # First Goal
    first_home = sum(
        (row["Home Goal FT"] > 0) and (row["Home Goal FT"] > row["Away Goal FT"])
        for _, row in matches.iterrows()
    )
    first_away = total_matches - first_home

    # Last Goal
    last_home = sum(
        (row["Home Goal FT"] > 0 and row["Home Goal FT"] >= row["Away Goal FT"])
        for _, row in matches.iterrows()
    )
    last_away = total_matches - last_home

    # 2+ e 2- situations
    two_up = sum(
        abs(row["Home Goal FT"] - row["Away Goal FT"]) >= 2
        for _, row in matches.iterrows()
    )

    two_down = two_up  # perché se uno è sopra di 2, l’altro è sotto di 2

    # HT Results
    ht_home_wins = sum(row["Home Goal 1T"] > row["Away Goal 1T"] for _, row in matches.iterrows())
    ht_draws = sum(row["Home Goal 1T"] == row["Away Goal 1T"] for _, row in matches.iterrows())
    ht_away_wins = sum(row["Home Goal 1T"] < row["Away Goal 1T"] for _, row in matches.iterrows())

    # 2nd half results
    sh_home_wins = sum(
        (row["Home Goal FT"] - row["Home Goal 1T"]) > (row["Away Goal FT"] - row["Away Goal 1T"])
        for _, row in matches.iterrows()
    )
    sh_draws = sum(
        (row["Home Goal FT"] - row["Home Goal 1T"]) == (row["Away Goal FT"] - row["Away Goal 1T"])
        for _, row in matches.iterrows()
    )
    sh_away_wins = total_matches - sh_home_wins - sh_draws

    # TODO - dettagli intermedi come 1-0, 1-1, ecc. (richiede analisi minuti goal)

    goal_patterns = {
        "P": total_matches,
        "H %": pct(home_wins),
        "D %": pct(draws),
        "A %": pct(away_wins),
        "First Home %": pct(first_home),
        "First Away %": pct(first_away),
        "Last Home %": pct(last_home),
        "Last Away %": pct(last_away),
        "2+ %": pct(two_up),
        "2- %": pct(two_down),
        "H 1st %": pct(ht_home_wins),
        "D 1st %": pct(ht_draws),
        "A 1st %": pct(ht_away_wins),
        "H 2nd %": pct(sh_home_wins),
        "D 2nd %": pct(sh_draws),
        "A 2nd %": pct(sh_away_wins)
    }

    df_patterns = pd.DataFrame([goal_patterns])
    st.table(df_patterns)

    # Grafico a barre
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(goal_patterns.keys())[1:],
        y=list(goal_patterns.values())[1:],
        text=[f"{v}%" for v in list(goal_patterns.values())[1:]],
        textposition='outside',
        marker_color='lightblue'
    ))

    fig.update_layout(
        title=f"Goal Patterns - {team1} vs {team2}",
        yaxis_title="Percentage (%)",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

