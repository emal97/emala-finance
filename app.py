import streamlit as st

STRIPE_PAYMENT_LINK = "https://buy.stripe.com/test_3cI00cdv72bm3xh5gocs800"

if "is_pro" not in st.session_state:
    st.session_state["is_pro"] = False

menu = st.sidebar.radio(
    "Navigation", 
    ["Analyse Technique", "Analyse Fondamentale", "Actualités", "Simulateur DCA (Pro)", "Comparateur (Pro)"]
)

def show_paywall():
    st.warning("🔒 **Fonctionnalité réservée aux membres Emala Finance Pro**")
    st.write("Débloque le Simulateur DCA et le Comparateur multi-actions pour seulement **9,99 € / mois**.")
    st.link_button("🚀 Passer à Emala Finance Pro", STRIPE_PAYMENT_LINK)
    st.divider()
    code = st.text_input("Déjà abonné ? Entre ton code d'accès :", type="password")
    if code == "EMALA_PRO_2026":
        st.session_state["is_pro"] = True
        st.success("Accès Pro activé !")
        st.rerun()

# --- GESTION DES PAGES ---

if menu == "Analyse Technique":
    # Mettre ici ton code pour l'Analyse Technique
    st.title("📈 Analyse Technique")

elif menu == "Analyse Fondamentale":
    # Mettre ici ton code pour l'Analyse Fondamentale
    st.title("📊 Analyse Fondamentale")

elif menu == "Actualités":
    # Mettre ici ton code pour les Actualités
    st.title("📰 Actualités")

elif menu == "Simulateur DCA (Pro)":
    if not st.session_state["is_pro"]:
        show_paywall()
    else:
        st.title("📈 Simulateur DCA")
        # Mettre ici ton code du simulateur DCA

elif menu == "Comparateur (Pro)":
    if not st.session_state["is_pro"]:
        show_paywall()
    else:
        st.title("📊 Comparateur multi-actions")
        # Mettre ici ton code du comparateur
