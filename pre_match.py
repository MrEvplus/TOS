import streamlit as st
import pandas as pd

from squadre import compute_team_macro_stats

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

        st.markdown("---")
        st.markdown("## 📊 Confronto Statistiche Pre-Match")

        # Calcola macro stats
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
def compute_team_macro_stats(df, team, venue):
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
        return {}

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
        "Matches Played": total_matches,
        "Win %": round((wins / total_matches) * 100, 2),
        "Draw %": round((draws / total_matches) * 100, 2),
        "Loss %": round((losses / total_matches) * 100, 2),
        "Avg Goals Scored": round(goals_for, 2),
        "Avg Goals Conceded": round(goals_against, 2),
        "BTTS %": round(btts, 2)
    }
    return stats
