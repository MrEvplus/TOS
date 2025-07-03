import streamlit as st

def run_team_stats(df, db_selected):
    st.title(f"Statistiche per Squadre - {db_selected}")
    st.info("🔧 Qui potrai implementare il calcolo di statistiche per singola squadra, medie gol fatti/subiti, over %, ecc.")
