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
        show_goal_patterns(df_filtered, team_1, team_2, db_selected, seasons_selected[0])

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

    # DEBUG: mostra tutte le partite home con flag se giocate
    data_debug = data.copy()
    data_debug["played_flag"] = data_debug.apply(is_match_played, axis=1)

    st.write("✅ TUTTE LE PARTITE FILTRATE:")
    st.dataframe(
        data_debug[[
            "Home", "Away", "Data", "Orario", 
            "Home Goal FT", "Away Goal FT", 
            "minuti goal segnato home", "minuti goal segnato away", 
            "played_flag"
        ]]
    )

    # Visualizza solo quelle escluse
    excluded = data_debug[data_debug["played_flag"] == False]
    if len(excluded) > 0:
        st.warning("⚠️ PARTITE ESCLUSE DAL CONTEGGIO:")
        st.dataframe(
            excluded[[
                "Home", "Away", "Data", "Orario",
                "Home Goal FT", "Away Goal FT",
                "minuti goal segnato home", "minuti goal segnato away"
            ]]
       )
    else:
        st.success("✅ Nessuna partita esclusa dal conteggio.")


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
def show_goal_patterns(df, team1, team2, country, stagione):
    df_team1_home = df[
        (df["Home"] == team1) &
        (df["country"] == country) &
        (df["Stagione"] == stagione)
    ]
    df_team2_away = df[
        (df["Away"] == team2) &
        (df["country"] == country) &
        (df["Stagione"] == stagione)
    ]

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
# LOGICA PER MATCH GIOCATO
# --------------------------------------------------------
def is_match_played(row):
    # se c'è almeno 1 goal registrato tramite minuti, la partita è giocata
    if pd.notna(row["minuti goal segnato home"]) and row["minuti goal segnato home"].strip() != "":
        return True
    if pd.notna(row["minuti goal segnato away"]) and row["minuti goal segnato away"].strip() != "":
        return True

    # se è 0-0 ma esiste un risultato FT → consideriamo giocata
    goals_home = row.get("Home Goal FT", None)
    goals_away = row.get("Away Goal FT", None)

    if pd.notna(goals_home) and pd.notna(goals_away):
        return True

    return False

def parse_datetime_excel(row):
    try:
        data_str = str(row["Data"]).strip()
        ora_str = str(row["Orario"]).zfill(4)

        if "-" in data_str:
            # es. 2025-03-16
            anno, mese, giorno = map(int, data_str.split("-"))
        elif "/" in data_str:
            # es. 16/03/2025
            giorno, mese, anno = map(int, data_str.split("/"))
        else:
            return None

        ora = int(ora_str[:2])
        minuto = int(ora_str[2:])

        dt = datetime(anno, mese, giorno, ora, minuto)
        return dt
    except:
        return None


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

        zero_zero_count = sum(
            (row["Home Goal FT"] == 0) and (row["Away Goal FT"] == 0)
            for _, row in df_team.iterrows()
        )
    else:
        wins = sum(df_team["Away Goal FT"] > df_team["Home Goal FT"])
        draws = sum(df_team["Away Goal FT"] == df_team["Home Goal FT"])
        losses = sum(df_team["Away Goal FT"] < df_team["Home Goal FT"])

        zero_zero_count = sum(
            (row["Away Goal FT"] == 0) and (row["Home Goal FT"] == 0)
            for _, row in df_team.iterrows()
        )

    zero_zero_pct = round((zero_zero_count / total_matches) * 100, 2) if total_matches > 0 else 0

    tf_scored = {f"{a}-{b}": 0 for a, b in timeframes()}
    tf_conceded = {f"{a}-{b}": 0 for a, b in timeframes()}

    first_goal = last_goal = one_zero = one_one_after_one_zero = 0
    two_zero_after_one_zero = zero_one = one_one_after_zero_one = zero_two_after_zero_one = 0

    for _, row in df_team.iterrows():
        timeline = build_timeline(row, venue)
        if not timeline:
            continue

        score_home = 0
        score_away = 0
        one_zero_found = False
        zero_one_found = False
        checked_one_one_after_one_zero = False
        checked_two_zero_after_one_zero = False
        checked_one_one_after_zero_one = False
        checked_zero_two_after_zero_one = False

        for team_char, minute in timeline:
            if team_char == "H":
                score_home += 1
            else:
                score_away += 1

            for start, end in timeframes():
                if start < minute <= end:
                    if venue == "Home":
                        if team_char == "H":
                            tf_scored[f"{start}-{end}"] += 1
                        else:
                            tf_conceded[f"{start}-{end}"] += 1
                    else:
                        if team_char == "A":
                            tf_scored[f"{start}-{end}"] += 1
                        else:
                            tf_conceded[f"{start}-{end}"] += 1

            if venue == "Home":
                if not one_zero_found and score_home == 1 and score_away == 0:
                    one_zero += 1
                    one_zero_found = True
                if one_zero_found and not checked_one_one_after_one_zero and score_home == 1 and score_away == 1:
                    one_one_after_one_zero += 1
                    checked_one_one_after_one_zero = True
                if one_zero_found and not checked_two_zero_after_one_zero and score_home == 2 and score_away == 0:
                    two_zero_after_one_zero += 1
                    checked_two_zero_after_one_zero = True

                if not zero_one_found and score_home == 0 and score_away == 1:
                    zero_one += 1
                    zero_one_found = True
                if zero_one_found and not checked_one_one_after_zero_one and score_home == 1 and score_away == 1:
                    one_one_after_zero_one += 1
                    checked_one_one_after_zero_one = True
                if zero_one_found and not checked_zero_two_after_zero_one and score_home == 0 and score_away == 2:
                    zero_two_after_zero_one += 1
                    checked_zero_two_after_zero_one = True

            elif venue == "Away":
                if not one_zero_found and score_away == 1 and score_home == 0:
                    one_zero += 1
                    one_zero_found = True
                if one_zero_found and not checked_one_one_after_one_zero and score_away == 1 and score_home == 1:
                    one_one_after_one_zero += 1
                    checked_one_one_after_one_zero = True
                if one_zero_found and not checked_two_zero_after_one_zero and score_away == 2 and score_home == 0:
                    two_zero_after_one_zero += 1
                    checked_two_zero_after_one_zero = True

                if not zero_one_found and score_away == 0 and score_home == 1:
                    zero_one += 1
                    zero_one_found = True
                if zero_one_found and not checked_one_one_after_zero_one and score_away == 1 and score_home == 1:
                    one_one_after_zero_one += 1
                    checked_one_one_after_zero_one = True
                if zero_one_found and not checked_zero_two_after_zero_one and score_away == 0 and score_home == 2:
                    zero_two_after_zero_one += 1
                    checked_zero_two_after_zero_one = True

    two_up = sum(
        abs(row["Home Goal FT"] - row["Away Goal FT"]) >= 2
        for _, row in df_team.iterrows()
    )

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

    tf_scored_pct = {
        k: round((v / sum(tf_scored.values())) * 100, 2) if sum(tf_scored.values()) > 0 else 0
        for k, v in tf_scored.items()
    }
    tf_conceded_pct = {
        k: round((v / sum(tf_conceded.values())) * 100, 2) if sum(tf_conceded.values()) > 0 else 0
        for k, v in tf_conceded.items()
    }

    patterns = {
        "P": total_matches,
        "Win %": pct(wins),
        "Draw %": pct(draws),
        "Loss %": pct(losses),
        "First Goal %": pct(first_goal),
        "Last Goal %": pct(last_goal),
        "1-0 %": pct(one_zero),
        "1-1 after 1-0 %": pct(one_one_after_one_zero),
        "2-0 after 1-0 %": pct(two_zero_after_one_zero),
        "0-1 %": pct(zero_one),
        "1-1 after 0-1 %": pct(one_one_after_zero_one),
        "0-2 after 0-1 %": pct(zero_two_after_zero_one),
        "2+ Goals %": pct(two_up),
        "H 1st %": pct(ht_wins),
        "D 1st %": pct(ht_draws),
        "A 1st %": pct(ht_losses),
        "H 2nd %": pct(sh_wins),
        "D 2nd %": pct(sh_draws),
        "A 2nd %": pct(sh_losses),
        "0-0 %": zero_zero_pct,
    }

    return patterns, tf_scored_pct, tf_conceded_pct

# --------------------------------------------------------
# TOTALS
# --------------------------------------------------------
def compute_goal_patterns_total(patterns_home, patterns_away, total_home_matches, total_away_matches):
    total_matches = total_home_matches + total_away_matches
    total_patterns = {}

    for key in goal_pattern_keys():
        if key == "P":
            total_patterns["P"] = total_matches
        elif key in ["Win %", "Draw %", "Loss %"]:
            if key == "Win %":
                val = (patterns_home["Win %"] + patterns_away["Loss %"]) / 2
            elif key == "Draw %":
                val = (patterns_home["Draw %"] + patterns_away["Draw %"]) / 2
            elif key == "Loss %":
                val = (patterns_home["Loss %"] + patterns_away["Win %"]) / 2
            total_patterns[key] = round(val, 2)
        else:
            home_val = patterns_home.get(key, 0)
            away_val = patterns_away.get(key, 0)
            val = (
                (home_val * total_home_matches) + (away_val * total_away_matches)
            ) / total_matches if total_matches > 0 else 0
            total_patterns[key] = round(val, 2)

    return total_patterns
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
# TIMELINE
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

        if timeline:
            timeline.sort(key=lambda x: x[1])
            return timeline

        # timeline vuota → costruisco timeline fake
        h_ft = int(row.get("Home Goal FT", 0))
        a_ft = int(row.get("Away Goal FT", 0))
        fake_timeline = []
        for _ in range(h_ft):
            fake_timeline.append(("H", 90))
        for _ in range(a_ft):
            fake_timeline.append(("A", 91))
        return fake_timeline if fake_timeline else []

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
# KEYS LIST
# --------------------------------------------------------
def goal_pattern_keys():
    keys = [
        "P", "Win %", "Draw %", "Loss %", 
        "First Goal %", "Last Goal %",
        "1-0 %", "1-1 after 1-0 %", "2-0 after 1-0 %",
        "0-1 %", "1-1 after 0-1 %", "0-2 after 0-1 %",
        "2+ Goals %", "H 1st %", "D 1st %", "A 1st %",
        "H 2nd %", "D 2nd %", "A 2nd %, "0-0 %","
    ]
    for start, end in timeframes():
        keys.append(f"{start}-{end} Goals %")
    return keys
