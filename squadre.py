import streamlit as st
import pandas as pd
import numpy as np
from utils import extract_minutes

# -------------------------------------------
# Entry point
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
        show_team_macro_stats(df_filtered, team_1)

    if team_2 and team_2 != team_1:
        st.subheader(f"✅ Statistiche Macro per {team_2}")
        show_team_macro_stats(df_filtered, team_2)

        st.subheader(f"⚔️ Goal Patterns - {team_1} vs {team_2}")
        show_goal_patterns(df_filtered, team_1, team_2)

# -------------------------------------------
# Macro Stats
# -------------------------------------------
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

# -------------------------------------------
# Goal Patterns
# -------------------------------------------
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

    # Calcoli base
    home_wins = sum(matches["Home Goal FT"] > matches["Away Goal FT"])
    draws = sum(matches["Home Goal FT"] == matches["Away Goal FT"])
    away_wins = sum(matches["Home Goal FT"] < matches["Away Goal FT"])

    first_home = sum(
        (row["Home Goal FT"] > 0 and row["Home Goal FT"] > row["Away Goal FT"])
        for _, row in matches.iterrows()
    )
    first_away = total_matches - first_home

    last_home = sum(
        (row["Home Goal FT"] > 0 and row["Home Goal FT"] >= row["Away Goal FT"])
        for _, row in matches.iterrows()
    )
    last_away = total_matches - last_home

    two_up = sum(abs(row["Home Goal FT"] - row["Away Goal FT"]) >= 2 for _, row in matches.iterrows())

    ht_home_wins = sum(row["Home Goal 1T"] > row["Away Goal 1T"] for _, row in matches.iterrows())
    ht_draws = sum(row["Home Goal 1T"] == row["Away Goal 1T"] for _, row in matches.iterrows())
    ht_away_wins = sum(row["Home Goal 1T"] < row["Away Goal 1T"] for _, row in matches.iterrows())

    sh_home_wins = sum(
        (row["Home Goal FT"] - row["Home Goal 1T"]) > (row["Away Goal FT"] - row["Away Goal 1T"])
        for _, row in matches.iterrows()
    )
    sh_draws = sum(
        (row["Home Goal FT"] - row["Home Goal 1T"]) == (row["Away Goal FT"] - row["Away Goal 1T"])
        for _, row in matches.iterrows()
    )
    sh_away_wins = total_matches - sh_home_wins - sh_draws

    # Totali
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
        "2- %": pct(two_up),  # stesso valore
        "H 1st %": pct(ht_home_wins),
        "D 1st %": pct(ht_draws),
        "A 1st %": pct(ht_away_wins),
        "H 2nd %": pct(sh_home_wins),
        "D 2nd %": pct(sh_draws),
        "A 2nd %": pct(sh_away_wins)
    }

    # Trasforma valori in HTML con barre
    html_table = build_goal_pattern_html(goal_patterns, team1, team2)
    st.markdown(html_table, unsafe_allow_html=True)

# -------------------------------------------
# HTML Table builder
# -------------------------------------------
def build_goal_pattern_html(patterns, team1, team2):
    def bar_html(value, color, width_max=80):
        width = int(width_max * (value/100))
        return f"""
        <div style='display: flex; align-items: center;'>
            <div style='height: 10px; width: {width}px; background-color: {color}; margin-right: 5px;'></div>
            <span style='font-size: 12px;'>{value:.1f}%</span>
        </div>
        """

    colors = {
        "H %": "green",
        "D %": "gold",
        "A %": "red",
        "First Home %": "green",
        "First Away %": "red",
        "Last Home %": "green",
        "Last Away %": "red",
        "2+ %": "blue",
        "2- %": "orange",
        "H 1st %": "green",
        "D 1st %": "gold",
        "A 1st %": "red",
        "H 2nd %": "green",
        "D 2nd %": "gold",
        "A 2nd %": "red"
    }

    rows = ""
    rows += f"<tr><th> </th>" + "".join(f"<th>{key}</th>" for key in patterns.keys()) + "</tr>"

    # Squadra Home
    row_home = f"<tr><td>{team1}</td>"
    for key, value in patterns.items():
        color = colors.get(key, "lightgray")
        cell = bar_html(value, color) if key != "P" else str(value)
        row_home += f"<td>{cell}</td>"
    row_home += "</tr>"

    # Squadra Away
    row_away = f"<tr><td>{team2}</td>"
    for key, value in patterns.items():
        color = colors.get(key, "lightgray")
        cell = bar_html(value, color) if key != "P" else str(value)
        row_away += f"<td>{cell}</td>"
    row_away += "</tr>"

    # Totale
    row_total = f"<tr style='font-weight:bold;'><td>Totale</td>"
    for key, value in patterns.items():
        color = colors.get(key, "lightgray")
        cell = bar_html(value, color) if key != "P" else str(value)
        row_total += f"<td>{cell}</td>"
    row_total += "</tr>"

    table_html = f"""
    <table style='border-collapse: collapse; width: 100%; font-size: 12px;'>
        {rows}
        {row_home}
        {row_away}
        {row_total}
    </table>
    """

    return table_html

