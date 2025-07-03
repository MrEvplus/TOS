import streamlit as st

def run_pre_match():
    st.title("Confronto Pre Match")

    squadra_casa = st.text_input("Squadra Casa")
    squadra_ospite = st.text_input("Squadra Ospite")

    col1, col2, col3 = st.columns(3)
    with col1:
        odd_home = st.number_input("Quota Vincente Casa", min_value=1.01, step=0.01)
    with col2:
        odd_draw = st.number_input("Quota Pareggio", min_value=1.01, step=0.01)
    with col3:
        odd_away = st.number_input("Quota Vincente Ospite", min_value=1.01, step=0.01)

    if squadra_casa and squadra_ospite:
        implied_home = round(100 / odd_home, 2)
        implied_draw = round(100 / odd_draw, 2)
        implied_away = round(100 / odd_away, 2)

        st.write(f"**Probabilità implicita:**")
        st.write(f"- Casa: {implied_home}%")
        st.write(f"- Pareggio: {implied_draw}%")
        st.write(f"- Ospite: {implied_away}%")

        st.info("🔧 Qui potrai integrare il confronto con statistiche storiche e ROI.")
