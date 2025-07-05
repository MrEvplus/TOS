import streamlit as st
import pandas as pd
from utils import label_match
from squadre import compute_team_macro_stats
from macros import run_macro_stats

# --------------------------------------------------------
# FUNZIONE PER OTTENERE LEAGUE DATA BY LABEL
# --------------------------------------------------------
def get_league_data_by_label(df, label):
    """
    Restituisce un dict con le stats della League per uno specifico Label.
    """
    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    # Costruisci campo match_result
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
# COMPUTE BOOKIE STATS
# --------------------------------------------------------
def compute_bookie_stats(df, label, market, team=None, bet_type="back"):
    if team:
        if label:
            if market == "Home":
                df_filtered = df[(df["Label"] == label) & (df["Home"] == team)]
            elif market == "Away":
                df_filtered = df[(df["Label"] == label) & (df["Away"] == team)]
            elif market == "Draw":
                df_filtered = df[(df["Label"] == label)]
            else:
                return 0, 0, 0, 0
        else:
            if market == "Home":
                df_filtered = df[df["Home"] == team]
            elif market == "Away":
                df_filtered = df[df["Away"] == team]
            elif market == "Draw":
                df_filtered = df
            else:
                return 0, 0, 0, 0
    else:
        if label:
            df_filtered = df[(df["Label"] == label)]
        else:
            df_filtered = df

    if df_filtered.empty:
        return 0, 0, 0, 0

    profit = 0
    wins = 0

    for _, row in df_filtered.iterrows():
        result_home = row.get("Home Goal FT", None)
        result_away = row.get("Away Goal FT", None)

        if result_home is None or result_away is None:
            continue

        if market == "Home":
            won_bet = result_home > result_away
            price = row.get("start_price_home", 0)

        elif market == "Draw":
            won_bet = result_home == result_away
            price = row.get("start_price_draw", 0)

        elif market == "Away":
            won_bet = result_away > result_home
            price = row.get("start_price_away", 0)

        else:
            continue

        if not price or price <= 1:
            continue

        if bet_type == "back":
            stake = 1
            if won_bet:
                profit += (price - 1) * stake
                wins += 1
            else:
                profit -= stake
        else:
            # LAY logic → liability fissa a 1 punto
            stake = 1 / (price - 1)
            if not won_bet:
                profit += stake
                wins += 1
            else:
                profit -= 1

    matches = len(df_filtered)
    win_pct = (wins / matches) * 100 if matches > 0 else 0
    roi = (profit / matches) * 100 if matches > 0 else 0

    return round(win_pct, 2), round(profit, 2), round(roi, 2), matches

# --------------------------------------------------------
# RUN PRE MATCH PAGE
# --------------------------------------------------------
def run_pre_match(df, db_selected):
    st.title("⚔️ Confronto Pre Match")

    # Assicura Label
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

        # Calcola Label
        label = label_from_odds(odd_home, odd_away)
        st.markdown(f"### 🎯 Range di quota identificato (Label): `{label}`")

        if label == "Others":
            st.info("⚠️ Le quote inserite non rientrano in nessun range di quota (Label). Verranno calcolate statistiche su TUTTO il campionato.")
            label = None
        elif label not in df["Label"].unique() or df[df["Label"] == label].empty:
            st.info(f"⚠️ Nessuna partita trovata nel database per il Label `{label}`. Verranno calcolate statistiche su TUTTO il campionato.")
            label = None

        # League Data
        league_stats = get_league_data_by_label(df, label) if label else None

        # -------------------------------------------------------
        # BOOKIE PTS AND ROI TABLE
        # -------------------------------------------------------
        st.markdown("---")
        st.markdown("## 📊 Bookie Pts and ROI Table")

        rows = []

        # League row
        if league_stats:
            rows.append({
                "Label": "League",
                "Market": "Home",
                "Matches": int(league_stats["Matches"]),
                "Back Win %": round(league_stats["HomeWin_pct"], 2),
                "Back Pts": None,
                "Back ROI %": None,
                "Lay Win %": None,
                "Lay Pts": None,
                "Lay ROI %": None
            })
            rows.append({
                "Label": "League",
                "Market": "Draw",
                "Matches": int(league_stats["Matches"]),
                "Back Win %": round(league_stats["Draw_pct"], 2),
                "Back Pts": None,
                "Back ROI %": None,
                "Lay Win %": None,
                "Lay Pts": None,
                "Lay ROI %": None
            })
            rows.append({
                "Label": "League",
                "Market": "Away",
                "Matches": int(league_stats["Matches"]),
                "Back Win %": round(league_stats["AwayWin_pct"], 2),
                "Back Pts": None,
                "Back ROI %": None,
                "Lay Win %": None,
                "Lay Pts": None,
                "Lay ROI %": None
            })

        # Squadra Casa
        for market in ["Home", "Draw", "Away"]:
            win_pct_b, pts_b, roi_b, matches_b = compute_bookie_stats(df, None, market, squadra_casa, bet_type="back")
            win_pct_l, pts_l, roi_l, _ = compute_bookie_stats(df, None, market, squadra_casa, bet_type="lay")
            rows.append({
                "Label": squadra_casa,
                "Market": market,
                "Matches": matches_b,
                "Back Win %": win_pct_b,
                "Back Pts": pts_b,
                "Back ROI %": roi_b,
                "Lay Win %": win_pct_l,
                "Lay Pts": pts_l,
                "Lay ROI %": roi_l,
            })

        # Squadra Ospite
        for market in ["Home", "Draw", "Away"]:
            win_pct_b, pts_b, roi_b, matches_b = compute_bookie_stats(df, None, market, squadra_ospite, bet_type="back")
            win_pct_l, pts_l, roi_l, _ = compute_bookie_stats(df, None, market, squadra_ospite, bet_type="lay")
            rows.append({
                "Label": squadra_ospite,
                "Market": market,
                "Matches": matches_b,
                "Back Win %": win_pct_b,
                "Back Pts": pts_b,
                "Back ROI %": roi_b,
                "Lay Win %": win_pct_l,
                "Lay Pts": pts_l,
                "Lay ROI %": roi_l,
            })

        df_bookie = pd.DataFrame(rows)
        if not df_bookie.empty and len(df_bookie["Market"].unique()) > 0:
            df_bookie["Market"] = pd.Categorical(df_bookie["Market"], categories=["Home", "Draw", "Away"], ordered=True)
            df_bookie = df_bookie.sort_values(["Label", "Market"])
            df_pivot = df_bookie.pivot(index="Label", columns="Market")
            st.dataframe(df_pivot, use_container_width=True)
        else:
            st.info("⚠️ Nessun dato trovato per il range di quota selezionato.")

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
