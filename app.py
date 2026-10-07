import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Emala Finance Pro",
    page_icon="📈",
    layout="wide"
)

# --- CONFIGURATION STRIPE & SESSION ---
STRIPE_PAYMENT_LINK = "https://buy.stripe.com/test_3cI00cdV72bm3xh5gocs800"

if "is_pro" not in st.session_state:
    st.session_state["is_pro"] = False

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

# --- NAVIGATION ---
menu = st.sidebar.radio(
    "Navigation", 
    ["Analyse Technique", "Analyse Fondamentale", "Actualités", "Simulateur DCA (Pro)", "Comparateur (Pro)"]
)

# ==========================================
# 1. ANALYSE TECHNIQUE
# ==========================================
if menu == "Analyse Technique":
    st.title("📈 Analyse Technique")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        ticker = st.text_input("Symbole (ex: AAPL, MC.PA, TSLA)", value="AAPL")
        period = st.selectbox("Période", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
        show_sma = st.checkbox("Afficher Moyennes Mobiles (SMA 20/50)", value=True)
        show_bollinger = st.checkbox("Afficher Bandes de Bollinger", value=False)
        show_rsi = st.checkbox("Afficher RSI", value=True)
        show_macd = st.checkbox("Afficher MACD", value=True)

    with col2:
        df = yf.Ticker(ticker).history(period=period)
        if not df.empty:
            # Calculs Indicateurs
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            
            # Bollinger
            std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['SMA_20'] + (std * 2)
            df['BB_Lower'] = df['SMA_20'] - (std * 2)

            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

            # Configuration dynamique des graphiques
            rows = 1
            row_heights = [1.0]
            if show_rsi and show_macd:
                rows = 3
                row_heights = [0.6, 0.2, 0.2]
            elif show_rsi or show_macd:
                rows = 2
                row_heights = [0.7, 0.3]

            fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

            # Prix & Chandeliers
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prix"), row=1, col=1)

            if show_sma:
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="SMA 20", line=dict(color='orange', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name="SMA 50", line=dict(color='limegreen', width=1)), row=1, col=1)

            if show_bollinger:
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name="BB Haut", line=dict(color='gray', dash='dash')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name="BB Bas", line=dict(color='gray', dash='dash')), row=1, col=1)

            current_row = 2
            if show_rsi:
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple')), row=current_row, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
                current_row += 1

            if show_macd:
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD", line=dict(color='blue')), row=current_row, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name="Signal", line=dict(color='orange')), row=current_row, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name="Histogramme"), row=current_row, col=1)

            fig.update_layout(xaxis_rangeslider_visible=False, height=700)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Aucune donnée trouvée pour ce ticker.")

# ==========================================
# 2. ANALYSE FONDAMENTALE
# ==========================================
elif menu == "Analyse Fondamentale":
    st.title("📊 Analyse Fondamentale")
    ticker = st.text_input("Entrez le symbole (ex: AAPL, MC.PA)", value="AAPL")
    
    if ticker:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Prix Actuel", f"{info.get('currentPrice', 'N/A')} {info.get('currency', '')}")
        col2.metric("P/E Ratio (PER)", info.get('trailingPE', 'N/A'))
        col3.metric("Rendement Dividende", f"{round(info.get('dividendYield', 0) * 100, 2)}%" if info.get('dividendYield') else "N/A")
        col4.metric("Capitalisation", f"{round(info.get('marketCap', 0) / 1e9, 2)} B")

        st.subheader("Apropos de l'entreprise")
        st.write(info.get('longBusinessSummary', 'Aucune description disponible.'))

# ==========================================
# 3. ACTUALITÉS
# ==========================================
elif menu == "Actualités":
    st.title("📰 Actualités Financières")
    ticker = st.text_input("Ticker pour les actualités", value="AAPL")
    
    if ticker:
        news = yf.Ticker(ticker).news
        if news:
            for item in news[:5]:
                st.subheader(item.get('title'))
                st.write(f"Source : {item.get('publisher')} | [Lire l'article]({item.get('link')})")
                st.divider()
        else:
            st.info("Aucune actualité récente trouvée.")

# ==========================================
# 4. SIMULATEUR DCA (PRO)
# ==========================================
elif menu == "Simulateur DCA (Pro)":
    if not st.session_state["is_pro"]:
        show_paywall()
    else:
        st.title("📈 Simulateur DCA (Dollar-Cost Averaging)")
        
        col1, col2 = st.columns(2)
        with col1:
            mensuel = st.number_input("Investissement mensuel (€)", min_value=10, value=200, step=10)
            annees = st.slider("Durée de l'investissement (années)", 1, 30, 10)
            rendement = st.slider("Rendement annuel estimé (%)", 1.0, 15.0, 8.0)
            
        months = annees * 12
        rate = (1 + rendement/100)**(1/12) - 1
        
        capital_investi = []
        valeur_portefeuille = []
        
        total_investi = 0
        total_valeur = 0
        
        for m in range(1, months + 1):
            total_investi += mensuel
            total_valeur = (total_valeur + mensuel) * (1 + rate)
            capital_investi.append(total_investi)
            valeur_portefeuille.append(total_valeur)
            
        df_dca = pd.DataFrame({
            "Mois": list(range(1, months + 1)),
            "Capital Investi": capital_investi,
            "Valeur Portefeuille": valeur_portefeuille
        })
        
        with col2:
            st.metric("Total Investi", f"{round(total_investi, 2)} €")
            st.metric("Valeur Finale Estimée", f"{round(total_valeur, 2)} €", delta=f"+{round(total_valeur - total_investi, 2)} €")
            
        fig_dca = go.Figure()
        fig_dca.add_trace(go.Scatter(x=df_dca["Mois"], y=df_dca["Capital Investi"], name="Capital Investi", line=dict(color='gray', dash='dash')))
        fig_dca.add_trace(go.Scatter(x=df_dca["Mois"], y=df_dca["Valeur Portefeuille"], name="Valeur Portefeuille", line=dict(color='green')))
        st.plotly_chart(fig_dca, use_container_width=True)

# ==========================================
# 5. COMPARATEUR MULTI-ACTIONS (PRO)
# ==========================================
elif menu == "Comparateur (Pro)":
    if not st.session_state["is_pro"]:
        show_paywall()
    else:
        st.title("📊 Comparateur Multi-Actions")
        tickers_input = st.text_input("Entrez plusieurs tickers séparés par des virgules", value="AAPL, MSFT, GOOGL, MC.PA")
        period_comp = st.selectbox("Période de comparaison", ["1mo", "3mo", "6mo", "1y", "5y"], index=3)
        
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        
        if tickers:
            data = yf.download(tickers, period=period_comp)['Close']
            if not data.empty:
                # Normalisation en % de variation
                norm_data = (data / data.iloc[0] - 1) * 100
                fig_comp = go.Figure()
                for col in norm_data.columns:
                    fig_comp.add_trace(go.Scatter(x=norm_data.index, y=norm_data[col], name=col))
                fig_comp.update_layout(title="Performance comparée (%)", yaxis_title="Variation en %")
                st.plotly_chart(fig_comp, use_container_width=True)
