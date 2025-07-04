import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------
def run_team_stats(df, db_selected):
    st.header("📊 Statistiche per Squadre")

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

# --------------------------------------------------------
# MACRO STATS
# --------------------------------------------------------
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

    if venue == "Home":
        wins = sum(data["Home Goal FT"] > data["Away Goal FT"])
        draws = sum(data["Home Goal FT"] == data["Away Goal FT"])
        losses = sum(data["Home Goal FT"] < data["Away Goal FT"])
    else:
        wins = sum(data["Away Goal FT"] > data["Home Goal FT"])
        draws = sum(data["Away Goal FT"] == data["Home Goal FT"])
        losses = sum(data["Away Goal FT"] < data["Home Goal FT"])

    goals_for = data[goals_for_col].mean()
    goals_against = data[goals_against_col].mean()

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

# --------------------------------------------------------
# GOAL PATTERNS
# --------------------------------------------------------
def show_goal_patterns(df, team1, team2):
    df_team1_home = df[df["Home"] == team1]
    total_home_matches = len(df_team1_home)

    df_team2_away = df[df["Away"] == team2]
    total_away_matches = len(df_team2_away)

    patterns_home, tf_scored_home, tf_conceded_home = compute_goal_patterns(df_team1_home, "Home", total_home_matches)
    patterns_away, tf_scored_away, tf_conceded_away = compute_goal_patterns(df_team2_away, "Away", total_away_matches)

    html_home = build_goal_pattern_html(patterns_home, team1, "green")
    html_away = build_goal_pattern_html(patterns_away, team2, "red")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### {team1} (Home)")
        st.markdown(html_home, unsafe_allow_html=True)

    with col2:
        st.markdown(f"### {team2} (Away)")
        st.markdown(html_away, unsafe_allow_html=True)

    # Grafico Home
    st.markdown(f"### Distribuzione Goal Time Frame - {team1} (Home)")
    chart_home = plot_timeframe_goals(tf_scored_home, tf_conceded_home, team1)
    st.altair_chart(chart_home, use_container_width=True)

    # Grafico Away
    st.markdown(f"### Distribuzione Goal Time Frame - {team2} (Away)")
    chart_away = plot_timeframe_goals(tf_scored_away, tf_conceded_away, team2)
    st.altair_chart(chart_away, use_container_width=True)

# --------------------------------------------------------
# BUILD SINGLE TABLE
# --------------------------------------------------------
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
        clean_key = key.replace('%', '').strip()
        cell = str(value) if key == "P" else bar_html(value, color)
        rows += f"<tr><td>{clean_key}</td><td>{cell}</td></tr>"

    html_table = f"""
    <table style='border-collapse: collapse; width: 100%; font-size: 12px;'>
        {rows}
    </table>
    """
    return html_table

# --------------------------------------------------------
# PLOT TIMEFRAME GOALS
# --------------------------------------------------------
def plot_timeframe_goals(tf_scored_pct, tf_conceded_pct, team):
    data = pd.DataFrame({
        "TimeFrame": list(tf_scored_pct.keys()),
        "Goals Scored (%)": list(tf_scored_pct.values()),
        "Goals Conceded (%)": list(tf_conceded_pct.values())
    })

    df_melt = data.melt("TimeFrame", var_name="Tipo", value_name="Percentuale")

    chart = alt.Chart(df_melt)\
        .mark_bar()\
        .encode(
            x=alt.X("TimeFrame:N", sort=list(tf_scored_pct.keys()), title="Minute Intervals"),
            y=alt.Y("Percentuale:Q", title="Percentage (%)"),
            color=alt.Color("Tipo:N",
                            scale=alt.Scale(
                                domain=["Goals Scored (%)", "Goals Conceded (%)"],
                                range=["green", "red"]
                            )),
            tooltip=["Tipo", "TimeFrame", "Percentuale"]
        ).properties(
            width=500,
            height=200,
            title=f"Goal Time Frame % - {team}"
        )

    text = alt.Chart(df_melt)\
        .mark_text(
            dy=-5,
            color="black"
        ).encode(
            x="TimeFrame:N",
            y="Percentuale:Q",
            text=alt.Text("Percentuale:Q", format=".0f")
        )

    return chart + text

# --------------------------------------------------------
# COMPUTE GOAL PATTERNS
# --------------------------------------------------------
def compute_goal_patterns(df_team, venue, total_matches):
    if total_matches == 0:
        return {key: 0 for key in goal_pattern_keys()}, {}, {}

    def pct(count):
        return round((count / total_matches) * 100, 2) if total_matches > 0 else 0

    if venue == "Home":
        wins = sum(df_team["Home Goal FT"] > df_team["Away Goal FT"])
        draws = sum(df_team["Home Goal FT"] == df_team["Away Goal FT"])
        losses = sum(df_team["Home Goal FT"] < df_team["Away Goal FT"])
    else:
        wins = sum(df_team["Away Goal FT"] > df_team["Home Goal FT"])
        draws = sum(df_team["Away Goal FT"] == df_team["Home Goal FT"])
        losses = sum(df_team["Away Goal FT"] < df_team["Home Goal FT"])

    tf_scored = {f"{a}-{b}": 0 for a,b in timeframes()}
    tf_conceded = {f"{a}-{b}": 0 for a,b in timeframes()}

    for _, row in df_team.iterrows():
        timeline = build_timeline(row, venue)
        if not timeline:
            continue

        for team_, minute in timeline:
            for start, end in timeframes():
                if start < minute <= end:
                    if venue == "Home":
                        if team_ == "H":
                            tf_scored[f"{start}-{end}"] += 1
                        else:
                            tf_conceded[f"{start}-{end}"] += 1
                    else:
                        if team_ == "A":
                            tf_scored[f"{start}-{end}"] += 1
                        else:
                            tf_conceded[f"{start}-{end}"] += 1

    total_goals_scored = sum(tf_scored.values())
    total_goals_conceded = sum(tf_conceded.values())

    tf_scored_pct = {
        k: round((v / total_goals_scored) * 100, 2) if total_goals_scored > 0 else 0
        for k, v in tf_scored.items()
    }
    tf_conceded_pct = {
        k: round((v / total_goals_conceded) * 100, 2) if total_goals_conceded > 0 else 0
        for k, v in tf_conceded.items()
    }

    patterns = {
        "P": total_matches,
        "Win %": pct(wins),
        "Draw %": pct(draws),
        "Loss %": pct(losses)
    }

    return patterns, tf_scored_pct, tf_conceded_pct

# --------------------------------------------------------
# TIMEFRAMES
# --------------------------------------------------------
def timeframes():
    return [
        (0, 15),
        (16, 30),
        (31, 45),
        (46, 60),
        (61, 75),
        (76, 120)
    ]

# --------------------------------------------------------
# BUILD TIMELINE
# --------------------------------------------------------
def build_timeline(row, venue):
    try:
        h_goals = parse_goal_times(row.get("minuti goal segnato home", ""))
        a_goals = parse_goal_times(row.get("minuti goal segnato away", ""))
        timeline = []

        for m in h_goals:
            timeline.append(("H", m))
        for m in a_goals:
            timeline.append(("A", m))

        timeline.sort(key=lambda x: x[1])
        return timeline
    except:
        return []

def parse_goal_times(val):
    if pd.isna(val) or val == "":
        return []
    times = []
    for part in str(val).strip().split(";"):
        if part.strip().isdigit():
            times.append(int(part.strip()))
    return times

# --------------------------------------------------------
# KEYS
# --------------------------------------------------------
def goal_pattern_keys():
    return ["P", "Win %", "Draw %", "Loss %"]
