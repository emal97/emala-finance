import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import re

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Emala Finance Pro",
    page_icon="📈",
    layout="wide"
)

# --- CONFIGURATION STRIPE & SESSION ---
STRIPE_PAYMENT_LINK = "https://buy.stripe.com/test_3cI00cdV72bm3xh5gocs800"
ADMIN_CODE = "EMALA_PRO_2026"

if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

# --- SIDEBAR & AUTHENTIFICATION ---
with st.sidebar:
    st.header("⚡ Emala Finance Pro")
    
    if not st.session_state.is_pro:
        st.info("🔒 Mode Gratuit")
        st.markdown(f"[👉 **Débloquer la version Pro (9,99 €/mois)**]({STRIPE_PAYMENT_LINK})")
        st.divider()
        code_input = st.text_input("Code d'accès Pro / Admin :", type="password")
        if code_input == ADMIN_CODE:
            st.session_state.is_pro = True
            st.success("Accès Pro activé !")
            st.rerun()
    else:
        st.success("👑 Statut : MEMBRE PRO")

    st.divider()
    menu = st.radio(
        "Navigation",
        ["Analyse Technique", "Analyse Fondamentale", "Actualités", "Simulateur DCA (Pro)", "Comparateur (Pro)"]
    )

# --- FONCTIONS REUTILISABLES ET CACHÉES (ANTI-BLOCAGE) ---

@st.cache_data(ttl=1800)
def fetch_history(ticker, period="1y"):
    """Récupère l'historique de cours de manière robuste et en cache."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            df = yf.download(ticker, period=period, progress=False)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_fundamentals(ticker_input):
    """Récupère les fondamentaux via fast_info et API directes."""
    import re
    user_input = re.sub(r'[^a-zA-Z0-9 ]', '', ticker_input).strip().upper()
    
    TICKER_MAP = {
        "NVIDIA": "NVDA", "APPLE": "AAPL", "MICROSOFT": "MSFT", 
        "TESLA": "TSLA", "GOOGLE": "GOOGL", "AMAZON": "AMZN"
    }
    ticker = TICKER_MAP.get(user_input, user_input)
    stock = yf.Ticker(ticker)
    
    price_val, mcap_val, per_val, div_val = "N/A", "N/A", "N/A", "N/A"
    
    # 1. fast_info (Prix & Capitalisation)
    try:
        fast = stock.fast_info
        price = getattr(fast, 'last_price', None)
        currency = getattr(fast, 'currency', 'USD')
        if price:
            price_val = f"{round(price, 2)} {currency}"
        mcap = getattr(fast, 'market_cap', None)
        if mcap:
            mcap_val = f"{round(mcap / 1e9, 2)} B {currency}"
    except Exception:
        pass

    # 2. QuoteSummary API (PER & Dividende)
    try:
        url_qs = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(ticker)}?modules=summaryDetail,defaultKeyStatistics"
        req = urllib.request.Request(url_qs, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=4)
        qs_data = json.loads(res.read().decode('utf-8'))
        
        result = qs_data.get('quoteSummary', {}).get('result', [])
        if result:
            summary_detail = result[0].get('summaryDetail', {})
            key_stats = result[0].get('defaultKeyStatistics', {})
            pe_raw = summary_detail.get('trailingPE', {}).get('raw') or key_stats.get('trailingPE', {}).get('raw')
            if pe_raw:
                per_val = f"{round(pe_raw, 2)}"
            div_raw = summary_detail.get('dividendYield', {}).get('raw')
            if div_raw is not None:
                div_val = f"{round(div_raw * 100, 2)}%"
            else:
                div_val = "0,0%"
    except Exception:
        pass

    # 3. Description Wikipédia
    summary_txt = None
    wiki_search = "Nvidia" if ticker == "NVDA" else ticker
    try:
        wiki_url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_search)}"
        req_wiki = urllib.request.Request(wiki_url, headers={'User-Agent': 'Mozilla/5.0'})
        res_wiki = urllib.request.urlopen(req_wiki, timeout=3)
        wiki_data = json.loads(res_wiki.read().decode('utf-8'))
        if 'extract' in wiki_data and "fait référence à" not in wiki_data['extract']:
            summary_txt = wiki_data['extract']
    except Exception:
        pass

    return ticker, price_val, per_val, div_val, mcap_val, summary_txt

# ==========================================
# 1. ANALYSE TECHNIQUE
# ==========================================
if menu == "Analyse Technique":
    st.title("📈 Analyse Technique")
    ticker = st.text_input("Symbole (ex: NVDA, AAPL, TSLA)", value="NVDA").strip().upper()
    period = st.selectbox("Période", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

    if ticker:
        df = fetch_history(ticker, period=period)
        if not df.empty and 'Close' in df.columns:
            # Calcul des indicateurs
            df['MM20'] = df['Close'].rolling(window=20).mean()
            df['MM50'] = df['Close'].rolling(window=50).mean()

            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            st.subheader(f"Évolution du cours - {ticker}")
            st.line_chart(df[['Close', 'MM20', 'MM50']])

            st.subheader("Indicateur RSI (14 jours)")
            st.line_chart(df['RSI'])
        else:
            st.error("Impossible de charger les données graphiques pour ce symbole.")

# ==========================================
# 2. ANALYSE FONDAMENTALE
# ==========================================
elif menu == "Analyse Fondamentale":
    st.title("📊 Analyse Fondamentale")
    user_input = st.text_input("Entrez le symbole ou le nom (ex: NVDA, NVIDIA, Apple)", value="NVDA")
    
    if user_input:
        ticker, price_val, per_val, div_val, mcap_val, summary_txt = fetch_fundamentals(user_input)

        st.caption(f"Ticker utilisé : **{ticker}**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Prix Actuel", price_val)
        col2.metric("P/E Ratio (PER)", per_val)
        col3.metric("Rendement Dividende", div_val)
        col4.metric("Capitalisation", mcap_val)

        st.subheader("À propos de l'entreprise")
        if summary_txt:
            st.write(summary_txt)
        else:
            st.info("Description indisponible pour ce symbole.")

# ==========================================
# 3. ACTUALITÉS
# ==========================================
elif menu == "Actualités":
    st.title("📰 Actualités Financières")
    ticker = st.text_input("Ticker ou entreprise pour les actualités", value="NVDA").strip()
    
    if ticker:
        try:
            query = f"{ticker} bourse action finance"
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=5).read()
            
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:5]
            
            if items:
                for item in items:
                    title = item.find('title').text if item.find('title') is not None else "Titre indisponible"
                    link = item.find('link').text if item.find('link') is not None else "#"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    
                    st.subheader(title)
                    if pub_date:
                        st.caption(f"📅 {pub_date[:16]}")
                    st.markdown(f"[👉 **Lire l'article complet**]({link})")
                    st.divider()
            else:
                st.info("Aucune actualité récente trouvée.")
        except Exception:
            st.error("Impossible de charger le flux d'actualités.")

# ==========================================
# 4. SIMULATEUR DCA (PRO)
# ==========================================
elif menu == "Simulateur DCA (Pro)":
    st.title("💰 Simulateur DCA (Dollar-Cost Averaging)")
    
    if not st.session_state.is_pro:
        st.warning("🔒 Cette fonctionnalité est réservée aux membres Pro.")
        st.markdown(f"[👉 **S'abonner pour 9,99 €/mois**]({STRIPE_PAYMENT_LINK})")
    else:
        col1, col2 = st.columns(2)
        ticker = col1.text_input("Symbole (ex: NVDA, AAPL, BTC-USD)", value="NVDA").strip().upper()
        montant_mensuel = col2.number_input("Investissement mensuel (€/$)", value=100, step=10)

        df = fetch_history(ticker, period="2y")
        if not df.empty and 'Close' in df.columns:
            # Resample mois par mois
            df_monthly = df['Close'].resample('ME').last().dropna()
            nb_mois = len(df_monthly)
            total_investi = nb_mois * montant_mensuel
            
            parts_cumulees = 0
            for price in df_monthly:
                parts_cumulees += montant_mensuel / price
                
            valeur_finale = parts_cumulees * df_monthly.iloc[-1]
            profit = valeur_finale - total_investi
            rendement = (profit / total_investi) * 100 if total_investi > 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Investi", f"{round(total_investi, 2)} $")
            m2.metric("Valeur Portefeuille", f"{round(valeur_finale, 2)} $")
            m3.metric("Gain / Perte", f"{round(profit, 2)} $", delta=f"{round(rendement, 2)}%")

            st.subheader("Historique des prix d'achat mensuels")
            st.line_chart(df_monthly)
        else:
            st.error("Données insuffisantes pour simuler le DCA.")

# ==========================================
# 5. COMPARATEUR (PRO)
# ==========================================
elif menu == "Comparateur (Pro)":
    st.title("⚔️ Comparateur Multi-Actions")
    
    if not st.session_state.is_pro:
        st.warning("🔒 Cette fonctionnalité est réservée aux membres Pro.")
        st.markdown(f"[👉 **S'abonner pour 9,99 €/mois**]({STRIPE_PAYMENT_LINK})")
    else:
        tickers_input = st.text_input("Entrez plusieurs tickers séparés par des virgules", value="NVDA, AAPL, MSFT")
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

        if tickers:
            comparison_df = pd.DataFrame()
            for t in tickers:
                df = fetch_history(t, period="1y")
                if not df.empty and 'Close' in df.columns:
                    # Normalisation base 100 pour comparer les performances
                    comparison_df[t] = (df['Close'] / df['Close'].iloc[0]) * 100

            if not comparison_df.empty:
                st.subheader("Performance comparée sur 1 an (Base 100)")
                st.line_chart(comparison_df)
            else:
                st.error("Impossible de récupérer les données pour la comparaison.")
