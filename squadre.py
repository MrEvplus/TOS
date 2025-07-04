import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime

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

    mask_played = data.apply(is_match_played, axis=1)
    data = data[mask_played]

    total_matches = len(data)

    if total_matches == 0:
        st.info("⚠️ Nessuna partita disputata trovata per la squadra selezionata.")
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

    btts_count = sum(
        (row["Home Goal FT"] > 0) and (row["Away Goal FT"] > 0)
        for _, row in data.iterrows()
    )
    btts = (btts_count / total_matches) * 100 if total_matches > 0 else 0

    stats = {
        "Venue": venue,
        "Matches": total_matches,
        "Win %": round((wins / total_matches) * 100, 2),
        "Draw %": round((draws / total_matches) * 100, 2),
        "Loss %": round((losses / total_matches) * 100, 2),
        "Avg Goals Scored": round(goals_for, 2),
        "Avg Goals Conceded": round(goals_against, 2),
        "BTTS %": round(btts, 2)
    }

    df_stats = pd.DataFrame([stats])
    st.dataframe(df_stats.set_index("Venue"), use_container_width=True)

# --------------------------------------------------------
# GOAL PATTERNS
# --------------------------------------------------------
def show_goal_patterns(df, team1, team2):
    df_team1_home = df[df["Home"] == team1]
    df_team2_away = df[df["Away"] == team2]

    mask_played_home = df_team1_home.apply(is_match_played, axis=1)
    df_team1_home = df_team1_home[mask_played_home]

    mask_played_away = df_team2_away.apply(is_match_played, axis=1)
    df_team2_away = df_team2_away[mask_played_away]

    total_home_matches = len(df_team1_home)
    total_away_matches = len(df_team2_away)

    patterns_home, tf_scored_home, tf_conceded_home = compute_goal_patterns(df_team1_home, "Home", total_home_matches)
    patterns_away, tf_scored_away, tf_conceded_away = compute_goal_patterns(df_team2_away, "Away", total_away_matches)

    patterns_total = compute_goal_patterns_total(
        patterns_home, patterns_away,
        total_home_matches, total_away_matches
    )

    html_home = build_goal_pattern_html(patterns_home, team1, "green")
    html_away = build_goal_pattern_html(patterns_away, team2, "red")
    html_total = build_goal_pattern_html(patterns_total, "Totale", "blue")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"### {team1} (Home)")
        st.markdown(html_home, unsafe_allow_html=True)

    with col2:
        st.markdown(f"### {team2} (Away)")
        st.markdown(html_away, unsafe_allow_html=True)

    with col3:
        st.markdown(f"### Totale")
        st.markdown(html_total, unsafe_allow_html=True)

    st.markdown(f"### Distribuzione Goal Time Frame - {team1} (Home)")
    chart_home = plot_timeframe_goals(tf_scored_home, tf_conceded_home, team1)
    st.altair_chart(chart_home, use_container_width=True)

    st.markdown(f"### Distribuzione Goal Time Frame - {team2} (Away)")
    chart_away = plot_timeframe_goals(tf_scored_away, tf_conceded_away, team2)
    st.altair_chart(chart_away, use_container_width=True)

# --------------------------------------------------------
# BUILD HTML TABLE
# --------------------------------------------------------
def build_goal_pattern_html(patterns, team, color):
    def bar_html(value, color, width_max=80):
        width = int(width_max * (value / 100))
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
# LOGICA PER MATCH GIOCATO (PATCH CORRETTA!)
# --------------------------------------------------------
def is_match_played(row):
    goals_sum = row["Home Goal FT"] + row["Away Goal FT"]

    if goals_sum > 0:
        return True

    if (pd.notna(row["minuti goal segnato home"]) and row["minuti goal segnato home"].strip() != ""):
        return True
    if (pd.notna(row["minuti goal segnato away"]) and row["minuti goal segnato away"].strip() != ""):
        return True

    dt_match = parse_datetime_excel(row)
    if dt_match:
        if dt_match < datetime.now():
            return True
        else:
            return False

    return False

def parse_datetime_excel(row):
    try:
        data_str = str(row["Data"]).strip()
        ora_str = str(row["Orario"]).zfill(4)

        giorno, mese, anno = map(int, data_str.split("/"))
        ora = int(ora_str[:2])
        minuto = int(ora_str[2:])

        dt = datetime(anno, mese, giorno, ora, minuto)
        return dt
    except:
        return None

# --------------------------------------------------------
# COMPUTE GOAL PATTERNS
# --------------------------------------------------------
def compute_goal_patterns(...):
    # TUTTO IL RESTO RESTA INVARIATO (usa quello già corretto dall'ultima versione che hai)

# --------------------------------------------------------
# RESTO FUNZIONI
# --------------------------------------------------------
# timeframes, build_timeline, parse_goal_times, etc.
# MANTIENI quelli che hai già corretti nell'ultima versione!
