import streamlit as st
import pandas as pd

from squadre import compute_team_macro_stats, is_match_played
from macros import label_match

# -------------------------------------------
# DETERMINA LABEL DALLA QUOTA
# -------------------------------------------
def label_from_odds(home_odd, away_odd):
    """
    Calcola la Label (range di quota) corrispondente alle quote inserite.
    Simula una riga del DB per usare label_match.
    """
    fake_row = {
        "start_price_home": home_odd,
        "start_price_away": away_odd
    }
    return label_match(fake_row)

# -------------------------------------------
# CALCOLA BOOKIE STATS SU DB
# -------------------------------------------
def compute_bookie_stats(df, label, market, team=None, bet_type="back"):
    """
    Calcola Win %, Pts e ROI per il mercato specificato (Home, Draw, Away).
    - bet_type: "back" oppure "lay"
    - team: se passato, filtra solo le partite di quella squadra.
    """
    if team:
        if market == "Home":
            df_filtered = df[(df["Label"] == label) & (df["Home"] == team)]
        elif market == "Away":
            df_filtered = df[(df["Label"] == label) & (df["Away"] == team)]
        else:
            df_filtered = df[(df["Label"] == label)]
    else:
        df_filtered = df[(df["Label"] == label)]

    if df_filtered.empty:
        return 0, 0, 0

    stake = 1
    profit = 0
    wins = 0

    for _, row in df_filtered.iterrows():
        result_home = row["Home Goal FT"]
        result_away = row["Away Goal FT"]

        if market == "Home":
            won_bet = result_home > result_away
            price = row["start_price_home"]

        elif market == "Draw":
            won_bet = result_home == result_away
            price = row["start_price_draw"]

        elif market == "Away":
            won_bet = result_away > result_home
            price = row["start_price_away"]

        # Calcolo back o lay
        if bet_type == "back":
            if won_bet:
                profit += (price - 1) * stake
                wins += 1
            else:
                profit -= stake
        else:
            # LAY logic → bancare vuol dire incassare stake se non esce il risultato
            if not won_bet:
                # Vincita netta = stake
                profit += stake
                wins += 1
            else:
                # Perdita = (lay odds - 1) * stake
                liability = (price - 1) * stake
                profit -= liability

    matches = len(df_filtered)
    win_pct = (wins / matches) * 100 if matches > 0 else 0
    roi = (profit / matches) * 100 if matches > 0 else 0

    return round(win_pct, 2), round(profit, 2), round(roi, 2)

# -------------------------------------------
# PAGINA STREAMLIT
# -------------------------------------------
def run_pre_match(df, db_selected):
    st.title("⚔️ Confronto Pre Match")

    # Filtro squadre disponibili
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

        # -------------------------------------------------------
        # CALCOLO LA LABEL DEL RANGE DI QUOTA
        # -------------------------------------------------------
        label = label_from_odds(odd_home, odd_away)
        st.markdown(f"### 🎯 Range di quota identificato (Label): `{label}`")

        # -------------------------------------------------------
        # BOOKIE PTS AND ROI TABLE
        # -------------------------------------------------------
        st.markdown("---")
        st.markdown("## 📊 Bookie Pts and ROI Table")

        rows = []
        for lbl, team in [("League", None), (squadra_casa, squadra_casa), (squadra_ospite, squadra_ospite)]:
            for market in ["Home", "Draw", "Away"]:
                win_pct_b, pts_b, roi_b = compute_bookie_stats(df, label, market, team, bet_type="back")
                win_pct_l, pts_l, roi_l = compute_bookie_stats(df, label, market, team, bet_type="lay")
                rows.append({
                    "Label": lbl,
                    "Market": market,
                    "Back Win %": win_pct_b,
                    "Back Pts": pts_b,
                    "Back ROI %": roi_b,
                    "Lay Win %": win_pct_l,
                    "Lay Pts": pts_l,
                    "Lay ROI %": roi_l
                })

        df_bookie = pd.DataFrame(rows)
        df_pivot = df_bookie.pivot(index="Label", columns="Market")
        st.dataframe(df_pivot, use_container_width=True)

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
