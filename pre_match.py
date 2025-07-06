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
# RUN PRE MATCH PAGE
# --------------------------------------------------------
def run_pre_match(df, db_selected):
    st.title("⚔️ Confronto Pre Match")

    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    teams_available = sorted(
        set(df[df["country"] == db_selected]["Home"].dropna().unique()) |
        set(df[df["country"] == db_selected]["Away"].dropna().unique())
    )

    squadra_casa = st.selectbox("Seleziona Squadra Casa", options=teams_available)
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

        league_stats = get_league_data_by_label(df, label) if label else None

        rows = []

        # League row
        if league_stats:
            row_league = {
                "LABEL": "League",
                "MATCHES": int(league_stats["Matches"]),
                "BACK WIN% HOME": round(league_stats["HomeWin_pct"], 2),
                "BACK WIN% DRAW": round(league_stats["Draw_pct"], 2),
                "BACK WIN% AWAY": round(league_stats["AwayWin_pct"], 2),
                "BACK PTS HOME": None,
                "BACK PTS DRAW": None,
                "BACK PTS AWAY": None,
                "BACK ROI% HOME": None,
                "BACK ROI% DRAW": None,
                "BACK ROI% AWAY": None,
                "Lay Win HOME": None,
                "Lay Win DRAW": None,
                "Lay Win AWAY": None,
                "Lay pts HOME": None,
                "Lay pts DRAW": None,
                "Lay pts AWAY": None,
                "lay ROI% HOME": None,
                "lay ROI% DRAW": None,
                "lay ROI% AWAY": None
            }
            rows.append(row_league)

        # ---------------------------
        # Squadra Casa
        # ---------------------------
        row_home = {"LABEL": squadra_casa}

        if label and label_type in ["Home", "Both"]:
            filtered_home = df[(df["Label"] == label) & (df["Home"] == squadra_casa)]
            matches_home = len(filtered_home)

            # Calcolo % win solo se ci sono partite
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
        else:
            row_home["MATCHES"] = "N/A"
            row_home["BACK WIN% HOME"] = 0
            row_home["BACK WIN% DRAW"] = 0
            row_home["BACK WIN% AWAY"] = 0

        # Metti 0 in tutte le altre colonne per ora
        for metric in ["BACK PTS", "BACK ROI%", "Lay Win", "Lay pts", "lay ROI%"]:
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_home[f"{metric} {outcome}"] = 0

        rows.append(row_home)

        # ---------------------------
        # Squadra Ospite
        # ---------------------------
        row_away = {"LABEL": squadra_ospite}

        if label and label_type in ["Away", "Both"]:
            filtered_away = df[(df["Label"] == label) & (df["Away"] == squadra_ospite)]
            matches_away = len(filtered_away)

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
        else:
            row_away["MATCHES"] = "N/A"
            row_away["BACK WIN% HOME"] = 0
            row_away["BACK WIN% DRAW"] = 0
            row_away["BACK WIN% AWAY"] = 0

        for metric in ["BACK PTS", "BACK ROI%", "Lay Win", "Lay pts", "lay ROI%"]:
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_away[f"{metric} {outcome}"] = 0

        rows.append(row_away)

        # ---------------------------
        # Stampa tabella finale
        # ---------------------------
        df_bookie = pd.DataFrame(rows)
        st.markdown(f"#### Range di quota identificato (Label): `{label}`")
        st.dataframe(df_bookie, use_container_width=True)

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
