import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import label_match, extract_minutes

def run_team_stats(df, db_selected):
    st.header("📊 Statistiche per Squadre")

    # Normalizza country e db_selected
    df["country"] = df["country"].fillna("").astype(str).str.strip().str.upper()
    db_selected = db_selected.strip().upper()

    # Check se il campionato esiste
    if db_selected not in df["country"].unique():
        st.warning(f"⚠️ Il campionato selezionato '{db_selected}' non è presente nel database.")
        st.stop()

    # Filtra campionato
    df_filtered = df[df["country"] == db_selected]

    # Trova stagioni disponibili
    seasons_available = sorted(df_filtered["Stagione"].dropna().unique().tolist(), reverse=True)

    if not seasons_available:
        st.warning(f"⚠️ Nessuna stagione disponibile nel database per il campionato {db_selected}.")
        st.stop()

    st.write(f"Stagioni disponibili nel database: {seasons_available}")

    # Seleziona stagioni
    seasons_selected = st.multiselect(
        "Seleziona le stagioni su cui vuoi calcolare le statistiche:",
        options=seasons_available,
        default=seasons_available[:1]
    )

    if not seasons_selected:
        st.warning("Seleziona almeno una stagione.")
        st.stop()

    # Filtra stagioni
    df_filtered = df_filtered[df_filtered["Stagione"].isin(seasons_selected)]

    # Trova squadre disponibili
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
    # Filtra Home
    df_home = df[df["Home"] == team]
    # Filtra Away
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

            btts = data["btts"].mean() * 100 if "btts" in data.columns else np.nan

            stats.append({
                "Venue": venue,
                "Matches": total_matches,
                "Win %": round((home_wins / total_matches) * 100, 2),
                "Draw %": round((draws / total_matches) * 100, 2),
                "Loss %": round((away_wins / total_matches) * 100, 2),
                "Avg Goals Scored": round(goals_for, 2),
                "Avg Goals Conceded": round(goals_against, 2),
                "BTTS %": round(btts, 2)
            })

    if stats:
        df_stats = pd.DataFrame(stats)
        st.dataframe(df_stats, use_container_width=True)
    else:
        st.info("⚠️ Nessuna partita trovata per la squadra selezionata.")


def show_goal_patterns(df, team1, team2):
    # Filtra solo le partite giocate tra le due squadre
    matches = df[
        ((df["Home"] == team1) & (df["Away"] == team2)) |
        ((df["Home"] == team2) & (df["Away"] == team1))
    ]

    if matches.empty:
        st.info("⚠️ Nessuna partita disponibile tra le due squadre selezionate.")
        return

    total_matches = len(matches)

    def calc_pct(count):
        return round((count / total_matches) * 100, 2) if total_matches > 0 else 0

    # Esempio base: % esiti finali
    h_wins = sum((matches["Home"] == team1) & (matches["Home Goal FT"] > matches["Away Goal FT"]))
    draws = sum(matches["Home Goal FT"] == matches["Away Goal FT"])
    a_wins = sum((matches["Away"] == team1) & (matches["Away Goal FT"] > matches["Home Goal FT"]))

    goal_patterns = {
        "P": total_matches,
        "H %": calc_pct(h_wins),
        "D %": calc_pct(draws),
        "A %": calc_pct(a_wins),
        # TODO: completare con tutte le colonne tecniche come nello screenshot
    }

    df_patterns = pd.DataFrame([goal_patterns])

    st.table(df_patterns)

    # Grafico barre
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Home Wins", "Draws", "Away Wins"],
        y=[goal_patterns["H %"], goal_patterns["D %"], goal_patterns["A %"]],
        text=[f"{goal_patterns['H %']}%", f"{goal_patterns['D %']}%", f"{goal_patterns['A %']}%"],
        textposition='outside',
        marker_color=['green', 'gold', 'red']
    ))

    fig.update_layout(
        title=f"Goal Patterns - {team1} vs {team2}",
        yaxis_title="Percentage (%)",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)
