import streamlit as st
import pandas as pd
import numpy as np

# -------------------------------------------
# ENTRY POINT
# -------------------------------------------
def run_team_stats(df, db_selected):
    st.header("📊 Statistiche per Squadre")

    # Normalizza valori
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

    # Seleziona stagioni
    seasons_selected = st.multiselect(
        "Seleziona le stagioni su cui vuoi calcolare le statistiche:",
        options=seasons_available,
        default=seasons_available[:1]
    )

    if not seasons_selected:
        st.warning("Seleziona almeno una stagione.")
        st.stop()

    df_filtered = df_filtered[df_filtered["Stagione"].isin(seasons_selected)]

    teams_available = sorted(
        set(df_filtered["Home"].dropna().unique()) |
        set(df_filtered["Away"].dropna().unique())
    )

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
        show_team_macro_stats(df_filtered, team_1, venue="Home")

    if team_2 and team_2 != team_1:
        st.subheader(f"✅ Statistiche Macro per {team_2}")
        show_team_macro_stats(df_filtered, team_2, venue="Away")

        st.subheader(f"⚔️ Goal Patterns - {team_1} vs {team_2}")
        show_goal_patterns(df_filtered, team_1, team_2)

# -------------------------------------------
# MACRO STATS
# -------------------------------------------
def show_team_macro_stats(df, team, venue):
    if venue == "Home":
        data = df[df["Home"] == team]
        goals_for_col = "Home Goal FT"
        goals_against_col = "Away Goal FT"
    else:
        data = df[df["Away"] == team]
        goals_for_col = "Away Goal FT"
        goals_against_col = "Home Goal FT"

    total_matches = len(data)

    if total_matches == 0:
        st.info("⚠️ Nessuna partita trovata per la squadra selezionata.")
        return

    # Risultati
    if venue == "Home":
        wins = sum(data["Home Goal FT"] > data["Away Goal FT"])
        draws = sum(data["Home Goal FT"] == data["Away Goal FT"])
        losses = sum(data["Home Goal FT"] < data["Away Goal FT"])
    else:
        wins = sum(data["Away Goal FT"] > data["Home Goal FT"])
        draws = sum(data["Away Goal FT"] == data["Home Goal FT"])
        losses = sum(data["Away Goal FT"] < data["Home Goal FT"])

    # Goals
    goals_for = data[goals_for_col].mean()
    goals_against = data[goals_against_col].mean()

    # BTTS corretto
    if "gg" in data.columns:
        btts = data["gg"].sum() / total_matches * 100
    else:
        btts = None

    stats = {
        "Venue": venue,
        "Matches": total_matches,
        "Win %": round((wins / total_matches) * 100, 2),
        "Draw %": round((draws / total_matches) * 100, 2),
        "Loss %": round((losses / total_matches) * 100, 2),
        "Avg Goals Scored": round(goals_for, 2),
        "Avg Goals Conceded": round(goals_against, 2),
        "BTTS %": round(btts, 2) if btts is not None else None
    }

    df_stats = pd.DataFrame([stats])
    st.dataframe(df_stats, use_container_width=True)

# -------------------------------------------
# GOAL PATTERNS
# -------------------------------------------
def show_goal_patterns(df, team1, team2):
    # Squadra 1 → Home
    df_team1_home = df[df["Home"] == team1]
    total_home_matches = len(df_team1_home)

    # Squadra 2 → Away
    df_team2_away = df[df["Away"] == team2]
    total_away_matches = len(df_team2_away)

    patterns_home = compute_goal_patterns(df_team1_home, "Home", total_home_matches)
    patterns_away = compute_goal_patterns(df_team2_away, "Away", total_away_matches)

    # Costruisci tabelle
    html_home = build_goal_pattern_html(patterns_home, team1, "green")
    html_away = build_goal_pattern_html(patterns_away, team2, "red")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### Goal Patterns - {team1} (Home)")
        st.markdown(html_home, unsafe_allow_html=True)

    with col2:
        st.markdown(f"### Goal Patterns - {team2} (Away)")
        st.markdown(html_away, unsafe_allow_html=True)

# -------------------------------------------
# COMPUTE GOAL PATTERNS
# -------------------------------------------
def compute_goal_patterns(df_team, venue, total_matches):
    if total_matches == 0:
        return {}

    def pct(count):
        return round((count / total_matches) * 100, 2) if total_matches > 0 else 0

    # Risultati finali
    if venue == "Home":
        wins = sum(df_team["Home Goal FT"] > df_team["Away Goal FT"])
        draws = sum(df_team["Home Goal FT"] == df_team["Away Goal FT"])
        losses = sum(df_team["Home Goal FT"] < df_team["Away Goal FT"])
    else:
        wins = sum(df_team["Away Goal FT"] > df_team["Home Goal FT"])
        draws = sum(df_team["Away Goal FT"] == df_team["Home Goal FT"])
        losses = sum(df_team["Away Goal FT"] < df_team["Home Goal FT"])

    # First / Last Goal
    first_goal = sum(
        row["Home Goal FT"] > row["Away Goal FT"]
        if venue == "Home"
        else row["Away Goal FT"] > row["Home Goal FT"]
        for _, row in df_team.iterrows()
    )
    last_goal = first_goal  # semplificazione se non hai minuti goal

    # Over +/- 2 goals
    two_up = sum(
        abs(row["Home Goal FT"] - row["Away Goal FT"]) >= 2
        for _, row in df_team.iterrows()
    )

    # HT results
    ht_wins = sum(
        row["Home Goal 1T"] > row["Away Goal 1T"]
        if venue == "Home"
        else row["Away Goal 1T"] > row["Home Goal 1T"]
        for _, row in df_team.iterrows()
    )
    ht_draws = sum(
        row["Home Goal 1T"] == row["Away Goal 1T"]
        for _, row in df_team.iterrows()
    )
    ht_losses = total_matches - ht_wins - ht_draws

    # SH results
    sh_wins = sum(
        (row["Home Goal FT"] - row["Home Goal 1T"]) >
        (row["Away Goal FT"] - row["Away Goal 1T"])
        if venue == "Home"
        else (row["Away Goal FT"] - row["Away Goal 1T"]) >
             (row["Home Goal FT"] - row["Home Goal 1T"])
        for _, row in df_team.iterrows()
    )
    sh_draws = sum(
        (row["Home Goal FT"] - row["Home Goal 1T"]) ==
        (row["Away Goal FT"] - row["Away Goal 1T"])
        for _, row in df_team.iterrows()
    )
    sh_losses = total_matches - sh_wins - sh_draws

    patterns = {
        "P": total_matches,
        "Win %": pct(wins),
        "Draw %": pct(draws),
        "Loss %": pct(losses),
        "First Goal %": pct(first_goal),
        "Last Goal %": pct(last_goal),
        "2+ Goals %": pct(two_up),
        "H 1st %": pct(ht_wins),
        "D 1st %": pct(ht_draws),
        "A 1st %": pct(ht_losses),
        "H 2nd %": pct(sh_wins),
        "D 2nd %": pct(sh_draws),
        "A 2nd %": pct(sh_losses)
    }
    return patterns

# -------------------------------------------
# BUILD HTML TABLE
# -------------------------------------------
def build_goal_pattern_html(patterns, team, color):
    def bar_html(value, color, width_max=80):
        width = int(width_max * (value/100))
        return f"""
        <div style='display: flex; align-items: center;'>
            <div style='height: 10px; width: {width}px; background-color: {color}; margin-right: 5px;'></div>
            <span style='font-size: 12px;'>{value:.1f}%</span>
        </div>
        """

    rows = f"<tr><th>Statistica</th><th>{team}</th></tr>"
    for key, value in patterns.items():
        cell = str(value) if key == "P" else bar_html(value, color)
        rows += f"<tr><td>{key}</td><td>{cell}</td></tr>"

    html_table = f"""
    <table style='border-collapse: collapse; width: 100%; font-size: 12px;'>
        {rows}
    </table>
    """

    return html_table
