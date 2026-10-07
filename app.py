import streamlit as st

# Ton lien Stripe généré
STRIPE_PAYMENT_LINK = "https://buy.stripe.com/test_3cI00cdv72bm3xh5gocs800"

# Initialisation de la session Pro
if "is_pro" not in st.session_state:
    st.session_state["is_pro"] = False

# Menu de navigation
menu = st.sidebar.radio(
    "Navigation", 
    ["Analyse Technique", "Analyse Fondamentale", "Actualités", "Simulateur DCA (Pro)", "Comparateur (Pro)"]
)

# Fonction pour afficher le Paywall
def show_paywall():
    st.warning("🔒 **Fonctionnalité réservée aux membres Emala Finance Pro**")
    st.write("Débloque le Simulateur DCA et le Comparateur multi-actions pour seulement **9,99 € / mois**.")
    
    # Bouton vers Stripe
    st.link_button("🚀 Passer à Emala Finance Pro", STRIPE_PAYMENT_LINK)
    
    st.divider()
    
    # Zone de déverrouillage pour les abonnés
    code = st.text_input("Déjà abonné ? Entre ton code d'accès :", type="password")
    if code == "EMALA_PRO_2026":  # Tu peux changer ce code de test
        st.session_state["is_pro"] = True
        st.success("Accès Pro activé !")
        st.rerun()

# Rendu des pages
if menu in ["Simulateur DCA (Pro)", "Comparateur (Pro)"] and not st.session_state["is_pro"]:
    show_paywall()
else:
    if menu == "Simulateur DCA (Pro)":
        st.title("📈 Simulateur DCA")
        # Code du simulateur...
    elif menu == "Comparateur (Pro)":
        st.title("📊 Comparateur multi-actions")
        # Code du comparateur...
