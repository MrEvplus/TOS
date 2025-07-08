from macros import calculate_goal_timeframes

def run_team_stats(df, db_selected):
    st.title(f"Statistiche per Squadre - {db_selected}")

    if df.empty:
        st.warning("⚠️ Il file è vuoto.")
        return

    st.info("Esempio di calcolo Goal Time Frame % su tutte le partite.")

    # Esempio: calcola sui totali
    scored_percents, conceded_percents = calculate_goal_timeframes(df, label="All")

    df_plot = pd.DataFrame({
        "TimeFrame": list(scored_percents.keys()),
        "Goals Scored (%)": list(scored_percents.values()),
        "Goals Conceded (%)": list(conceded_percents.values())
    })

    import plotly.express as px
    fig = px.bar(
        df_plot,
        x="TimeFrame",
        y=["Goals Scored (%)", "Goals Conceded (%)"],
        barmode="group",
        title=f"Goal Patterns - {db_selected}"
    )
    st.plotly_chart(fig, use_container_width=True)
