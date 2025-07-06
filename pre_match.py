import streamlit as st
import pandas as pd
from utils import label_match
from squadre import compute_team_macro_stats
from macros import run_macro_stats

# --------------------------------------------------------
# FUNZIONE PER OTTENERE LEAGUE DATA BY LABEL
# --------------------------------------------------------
def get_league_data_by_label(df, label):
    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    df["match_result"] = df.apply(
        lambda row: "Home Win" if row["Home Goal FT"] > row["Away Goal FT"]
        else "Away Win" if row["Home Goal FT"] < row["Away Goal FT"]
        else "Draw",
        axis=1
    )

    group_label = df.groupby("Label").agg(
        Matches=("Home", "count"),
        HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean() * 100),
        Draw_pct=("match_result", lambda x: (x == "Draw").mean() * 100),
        AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean() * 100)
    ).reset_index()

    row = group_label[group_label["Label"] == label]
    if not row.empty:
        return row.iloc[0].to_dict()
    else:
        return None

# --------------------------------------------------------
# LABEL FROM ODDS
# --------------------------------------------------------
def label_from_odds(home_odd, away_odd):
    fake_row = {
        "Odd home": home_odd,
        "Odd Away": away_odd
    }
    return label_match(fake_row)

# --------------------------------------------------------
# DETERMINA TIPO DI LABEL
# --------------------------------------------------------
def get_label_type(label):
    if label and label.startswith("H_"):
        return "Home"
    elif label and label.startswith("A_"):
        return "Away"
    else:
        return "Both"

# --------------------------------------------------------
# FORMATTING COLORE
# --------------------------------------------------------
def format_value(val, is_roi=False):
    if val is None:
        val = 0
    suffix = "%" if is_roi else ""
    if val > 0:
        return f"🟢 +{val:.2f}{suffix}"
    elif val < 0:
        return f"🔴 {val:.2f}{suffix}"
    else:
        return f"0.00{suffix}"
# --------------------------------------------------------
# CALCOLO BACK / LAY STATS (versione corretta)
# --------------------------------------------------------
def calculate_back_lay(filtered_df):
    """
    Calcola:
    - profitti back e lay
    - ROI% back e lay
    per HOME, DRAW, AWAY su tutte le righe di filtered_df.

    Per il LAY, la responsabilità è fissa a 1 unità.
    """
    profits_back = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    profits_lay = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    matches = len(filtered_df)

    for _, row in filtered_df.iterrows():
        h_goals = row["Home Goal FT"]
        a_goals = row["Away Goal FT"]

        result = (
            "HOME" if h_goals > a_goals else
            "AWAY" if h_goals < a_goals else
            "DRAW"
        )

        for outcome in ["HOME", "DRAW", "AWAY"]:
            # Leggi la quota corretta
            if outcome == "HOME":
                price = row.get("Odd home", None)
            elif outcome == "DRAW":
                price = row.get("Odd Draw", None)
            elif outcome == "AWAY":
                price = row.get("Odd Away", None)

            try:
                price = float(price)
            except:
                price = 2.00

            if price <= 1:
                price = 2.00

            # BACK
            if result == outcome:
                profits_back[outcome] += (price - 1)
            else:
                profits_back[outcome] -= 1

            # LAY corretto → responsabilità = 1
            stake = 1 / (price - 1)
            if result != outcome:
                profits_lay[outcome] += stake
            else:
                profits_lay[outcome] -= 1

    rois_back = {}
    rois_lay = {}
    for outcome in ["HOME", "DRAW", "AWAY"]:
        if matches > 0:
            rois_back[outcome] = round((profits_back[outcome] / matches) * 100, 2)
            rois_lay[outcome] = round((profits_lay[outcome] / matches) * 100, 2)
        else:
            rois_back[outcome] = 0
            rois_lay[outcome] = 0

    return profits_back, rois_back, profits_lay, rois_lay, matches

# --------------------------------------------------------
# RUN PRE MATCH PAGE
# --------------------------------------------------------
def run_pre_match(df, db_selected):
    st.title("⚔️ Confronto Pre Match")

    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    # Rimuovi eventuali spazi extra nei nomi squadre
    df["Home"] = df["Home"].str.strip()
    df["Away"] = df["Away"].str.strip()

    teams_available = sorted(
        set(df[df["country"] == db_selected]["Home"].dropna().unique()) |
        set(df[df["country"] == db_selected]["Away"].dropna().unique())
    )

    col1, col2 = st.columns(2)

    with col1:
        squadra_casa = st.selectbox("Seleziona Squadra Casa", options=teams_available)

    with col2:
        squadra_ospite = st.selectbox("Seleziona Squadra Ospite", options=teams_available)


    col1, col2, col3 = st.columns(3)
    with col1:
        odd_home = st.number_input("Quota Vincente Casa", min_value=1.01, step=0.01, value=2.00)
    with col2:
        odd_draw = st.number_input("Quota Pareggio", min_value=1.01, step=0.01, value=3.20)
    with col3:
        odd_away = st.number_input("Quota Vincente Ospite", min_value=1.01, step=0.01, value=3.80)

    if squadra_casa and squadra_ospite and squadra_casa != squadra_ospite:
        implied_home = round(100 / odd_home, 2)
        implied_draw = round(100 / odd_draw, 2)
        implied_away = round(100 / odd_away, 2)

        st.markdown(f"### 🎯 Probabilità implicite dalle quote:")
        st.write(f"- **Casa ({squadra_casa}):** {implied_home}%")
        st.write(f"- **Pareggio:** {implied_draw}%")
        st.write(f"- **Ospite ({squadra_ospite}):** {implied_away}%")

        label = label_from_odds(odd_home, odd_away)
        label_type = get_label_type(label)

        st.markdown(f"### 🎯 Range di quota identificato (Label): `{label}`")

        if label == "Others":
            st.info("⚠️ Le quote inserite non rientrano in nessun range di quota. Verranno calcolate statistiche su tutto il campionato.")
            label = None
        elif label not in df["Label"].unique() or df[df["Label"] == label].empty:
            st.info(f"⚠️ Nessuna partita trovata per il Label `{label}`. Verranno calcolate statistiche su tutto il campionato.")
            label = None

        rows = []

        # ---------------------------
        # League
        # ---------------------------
        if label:
            filtered_league = df[df["Label"] == label]
            profits_back, rois_back, profits_lay, rois_lay, matches_league = calculate_back_lay(filtered_league)

            league_stats = get_league_data_by_label(df, label)
            row_league = {
                "LABEL": "League",
                "MATCHES": matches_league,
                "BACK WIN% HOME": round(league_stats["HomeWin_pct"], 2) if league_stats else 0,
                "BACK WIN% DRAW": round(league_stats["Draw_pct"], 2) if league_stats else 0,
                "BACK WIN% AWAY": round(league_stats["AwayWin_pct"], 2) if league_stats else 0
            }
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_league[f"BACK PTS {outcome}"] = format_value(profits_back[outcome])
                row_league[f"BACK ROI% {outcome}"] = format_value(rois_back[outcome], is_roi=True)
                row_league[f"Lay pts {outcome}"] = format_value(profits_lay[outcome])
                row_league[f"lay ROI% {outcome}"] = format_value(rois_lay[outcome], is_roi=True)
            rows.append(row_league)

        # ---------------------------
        # Squadra Casa
        # ---------------------------
        row_home = {"LABEL": squadra_casa}
        if label and label_type in ["Home", "Both"]:
            filtered_home = df[(df["Label"] == label) & (df["Home"] == squadra_casa)]

            if filtered_home.empty:
                filtered_home = df[df["Home"] == squadra_casa]
                st.info(f"⚠️ Nessuna partita trovata per questo label. Calcolo eseguito su TUTTO il database per {squadra_casa}.")

            with st.expander(f"DEBUG - Partite Home per {squadra_casa}"):
                st.write(filtered_home)

            profits_back, rois_back, profits_lay, rois_lay, matches_home = calculate_back_lay(filtered_home)

            if matches_home > 0:
                wins_home = sum(filtered_home["Home Goal FT"] > filtered_home["Away Goal FT"])
                draws_home = sum(filtered_home["Home Goal FT"] == filtered_home["Away Goal FT"])
                losses_home = sum(filtered_home["Home Goal FT"] < filtered_home["Away Goal FT"])

                pct_win_home = round((wins_home / matches_home) * 100, 2)
                pct_draw = round((draws_home / matches_home) * 100, 2)
                pct_loss = round((losses_home / matches_home) * 100, 2)
            else:
                pct_win_home = pct_draw = pct_loss = 0

            row_home["MATCHES"] = matches_home
            row_home["BACK WIN% HOME"] = pct_win_home
            row_home["BACK WIN% DRAW"] = pct_draw
            row_home["BACK WIN% AWAY"] = pct_loss

            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_home[f"BACK PTS {outcome}"] = format_value(profits_back[outcome])
                row_home[f"BACK ROI% {outcome}"] = format_value(rois_back[outcome], is_roi=True)
                row_home[f"Lay pts {outcome}"] = format_value(profits_lay[outcome])
                row_home[f"lay ROI% {outcome}"] = format_value(rois_lay[outcome], is_roi=True)
        else:
            row_home["MATCHES"] = "N/A"
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_home[f"BACK WIN% {outcome}"] = 0
                row_home[f"BACK PTS {outcome}"] = format_value(0)
                row_home[f"BACK ROI% {outcome}"] = format_value(0, is_roi=True)
                row_home[f"Lay pts {outcome}"] = format_value(0)
                row_home[f"lay ROI% {outcome}"] = format_value(0, is_roi=True)
        rows.append(row_home)

        # ---------------------------
        # Squadra Ospite
        # ---------------------------
        row_away = {"LABEL": squadra_ospite}
        if label and label_type in ["Away", "Both"]:
            filtered_away = df[(df["Label"] == label) & (df["Away"] == squadra_ospite)]

            if filtered_away.empty:
                filtered_away = df[df["Away"] == squadra_ospite]
                st.info(f"⚠️ Nessuna partita trovata per questo label. Calcolo eseguito su TUTTO il database per {squadra_ospite}.")

            with st.expander(f"DEBUG - Partite Away per {squadra_ospite}"):
                st.write(filtered_away)

            profits_back, rois_back, profits_lay, rois_lay, matches_away = calculate_back_lay(filtered_away)

            if matches_away > 0:
                wins_away = sum(filtered_away["Away Goal FT"] > filtered_away["Home Goal FT"])
                draws_away = sum(filtered_away["Away Goal FT"] == filtered_away["Home Goal FT"])
                losses_away = sum(filtered_away["Away Goal FT"] < filtered_away["Home Goal FT"])

                pct_win_away = round((wins_away / matches_away) * 100, 2)
                pct_draw = round((draws_away / matches_away) * 100, 2)
                pct_loss = round((losses_away / matches_away) * 100, 2)
            else:
                pct_win_away = pct_draw = pct_loss = 0

            row_away["MATCHES"] = matches_away
            row_away["BACK WIN% HOME"] = pct_loss
            row_away["BACK WIN% DRAW"] = pct_draw
            row_away["BACK WIN% AWAY"] = pct_win_away

            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_away[f"BACK PTS {outcome}"] = format_value(profits_back[outcome])
                row_away[f"BACK ROI% {outcome}"] = format_value(rois_back[outcome], is_roi=True)
                row_away[f"Lay pts {outcome}"] = format_value(profits_lay[outcome])
                row_away[f"lay ROI% {outcome}"] = format_value(rois_lay[outcome], is_roi=True)
        else:
            row_away["MATCHES"] = "N/A"
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_away[f"BACK WIN% {outcome}"] = 0
                row_away[f"BACK PTS {outcome}"] = format_value(0)
                row_away[f"BACK ROI% {outcome}"] = format_value(0, is_roi=True)
                row_away[f"Lay pts {outcome}"] = format_value(0)
                row_away[f"lay ROI% {outcome}"] = format_value(0, is_roi=True)
        rows.append(row_away)

        # ------------------------------------------
        # CONVERSIONE TABELLA IN LONG FORMAT
        # ------------------------------------------
        rows_long = []
        for row in rows:
            for outcome in ["HOME", "DRAW", "AWAY"]:
                rows_long.append({
                    "LABEL": row["LABEL"],
                    "SEGNO": outcome,
                    "Matches": row["MATCHES"],
                    "Win %": row[f"BACK WIN% {outcome}"],
                    "Back Pts": row[f"BACK PTS {outcome}"],
                    "Back ROI %": row[f"BACK ROI% {outcome}"],
                    "Lay Pts": row[f"Lay pts {outcome}"],
                    "Lay ROI %": row[f"lay ROI% {outcome}"]
                })

        df_long = pd.DataFrame(rows_long)
        df_long.loc[df_long.duplicated(subset=["LABEL"]), "LABEL"] = ""

        st.markdown(f"#### Range di quota identificato (Label): `{label}`")
        st.dataframe(df_long, use_container_width=True)

        # -------------------------------------------------------
        # CONFRONTO MACRO STATS
        # -------------------------------------------------------
        st.markdown("---")
        st.markdown("## 📊 Confronto Statistiche Pre-Match")

        stats_home = compute_team_macro_stats(df, squadra_casa, "Home")
        stats_away = compute_team_macro_stats(df, squadra_ospite, "Away")

        if not stats_home or not stats_away:
            st.info("⚠️ Una delle due squadre non ha partite disponibili per il confronto.")
            return

        df_comp = pd.DataFrame({
            squadra_casa: stats_home,
            squadra_ospite: stats_away
        })

        st.dataframe(df_comp, use_container_width=True)

        st.success("✅ Confronto Pre Match generato con successo!")
