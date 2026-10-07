import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import re

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Emala Finance Pro — Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INJECTION CSS PREMIUM (DESIGN SAAS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    
    /* Cartes Métriques */
    .metric-card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 12px;
        padding: 18px 12px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #58A6FF;
    }
    .metric-label { color: #8B949E; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
    .metric-val { color: #F0F6FC; font-size: 1.5rem; font-weight: 700; margin-top: 6px; }
    .metric-sub { font-size: 0.8rem; margin-top: 4px; font-weight: 600; }
    .positive { color: #3FB950; }
    .negative { color: #F85149; }
    .neutral { color: #58A6FF; }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION STRIPE & SESSION ---
STRIPE_PAYMENT_LINK = "https://buy.stripe.com/test_3cI00cdV72bm3xh5gocs800"
ADMIN_CODE = "EMALA_PRO_2026"

if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚡ EMALA PRO")
    st.caption("Terminal d'Analyse Financière")
    
    if not st.session_state.is_pro:
        st.info("🔒 Mode Standard")
        st.markdown(f"[👉 **Débloquer la version Pro (9,99 €/mois)**]({STRIPE_PAYMENT_LINK})")
        st.divider()
        code_input = st.text_input("Code Secret Admin :", type="password")
        if code_input == ADMIN_CODE:
            st.session_state.is_pro = True
            st.success("Accès Pro activé !")
            st.rerun()
    else:
        st.success("👑 MEMBRE PRO ACTIVÉ")

    st.divider()
    menu = st.radio(
        "MODULES",
        ["Analyse Technique", "Analyse Fondamentale", "Actualités", "Simulateur DCA (Pro)", "Comparateur (Pro)"]
    )

# --- COMPOSANT METRIQUE PERSONNALISÉ ---
def render_metric(label, value, sub="", status="neutral"):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-val">{value}</div>
        <div class="metric-sub {status}">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

# --- CACHE DES DONNÉES ---
@st.cache_data(ttl=1800)
def fetch_history(ticker, period="1y"):
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
    user_input = re.sub(r'[^a-zA-Z0-9 ]', '', ticker_input).strip().upper()
    TICKER_MAP = {
        "NVIDIA": "NVDA", "APPLE": "AAPL", "MICROSOFT": "MSFT", 
        "TESLA": "TSLA", "GOOGLE": "GOOGL", "AMAZON": "AMZN"
    }
    ticker = TICKER_MAP.get(user_input, user_input)
    stock = yf.Ticker(ticker)
    
    price_val, mcap_val, per_val, div_val = "N/A", "N/A", "N/A", "N/A"
    high_52, low_52 = "N/A", "N/A"
    
    try:
        fast = stock.fast_info
        price = getattr(fast, 'last_price', None)
        currency = getattr(fast, 'currency', 'USD')
        if price:
            price_val = f"{round(price, 2)} {currency}"
        mcap = getattr(fast, 'market_cap', None)
        if mcap:
            mcap_val = f"{round(mcap / 1e9, 2)} B {currency}"
        
        h52 = getattr(fast, 'year_high', None)
        l52 = getattr(fast, 'year_low', None)
        if h52: high_52 = f"{round(h52, 2)} {currency}"
        if l52: low_52 = f"{round(l52, 2)} {currency}"
    except Exception:
        pass

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

    return ticker, price_val, per_val, div_val, mcap_val, high_52, low_52, summary_txt

# ==========================================
# 1. ANALYSE TECHNIQUE (GRAPHES INTERACTIFS)
# ==========================================
if menu == "Analyse Technique":
    st.title("📈 Analyse Technique Avancée")
    
    col_input, col_period = st.columns([3, 1])
    ticker = col_input.text_input("Symbole (ex: NVDA, AAPL, BTC-USD)", value="NVDA").strip().upper()
    period = col_period.selectbox("Horizon", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

    if ticker:
        df = fetch_history(ticker, period=period)
        if not df.empty and 'Close' in df.columns:
            # Calculs d'indicateurs
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Graphique interactif Plotly
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, 
                vertical_spacing=0.08, subplot_titles=(f"Cours & Moyennes Mobiles — {ticker}", "Indicateur RSI (14)"),
                row_width=[0.3, 0.7]
            )

            # Chandeliers ou ligne
            if 'Open' in df.columns and 'High' in df.columns:
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    name="Prix"
                ), row=1, col=1)
            else:
                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name="Prix", line=dict(color='#58A6FF', width=2)), row=1, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], mode='lines', name="EMA 20", line=dict(color='#E3B341', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], mode='lines', name="EMA 50", line=dict(color='#A371F7', width=1.5)), row=1, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name="RSI", line=dict(color='#F0883E', width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#F85149", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#3FB950", row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(22,27,34,0.8)",
                xaxis_rangeslider_visible=False,
                height=600,
                margin=dict(l=20, r=20, t=40, b=20)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Données graphiques indisponibles pour ce symbole.")

# ==========================================
# 2. ANALYSE FONDAMENTALE
# ==========================================
elif menu == "Analyse Fondamentale":
    st.title("📊 Analyse Fondamentale & Métriques")
    user_input = st.text_input("Symbole ou Nom de l'entreprise (ex: NVDA, NVIDIA, Apple)", value="NVDA")
    
    if user_input:
        ticker, price_val, per_val, div_val, mcap_val, high_52, low_52, summary_txt = fetch_fundamentals(user_input)

        st.caption(f"Ticker identifié : **{ticker}**")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_metric("Prix Actuel", price_val, "En direct", "neutral")
        with c2: render_metric("P/E Ratio (PER)", per_val, "Multiplicateur", "neutral")
        with c3: render_metric("Rendement Div.", div_val, "Annuel", "positive")
        with c4: render_metric("Capitalisation", mcap_val, "Valeur de marché", "neutral")

        st.markdown("<br>", unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        with c5: render_metric("Plus Haut (52 sem.)", high_52, "Sommet annuel", "positive")
        with c6: render_metric("Plus Bas (52 sem.)", low_52, "Creux annuel", "negative")

        st.subheader("📋 Profil & Activité de l'entreprise")
        if summary_txt:
            st.info(summary_txt)
        else:
            st.warning("Aucune description disponible pour ce symbole.")

# ==========================================
# 3. ACTUALITÉS
# ==========================================
elif menu == "Actualités":
    st.title("📰 Actualités Financières Temps Réel")
    ticker = st.text_input("Sujet ou Ticker", value="NVDA").strip()
    
    if ticker:
        try:
            query = f"{ticker} bourse action finance"
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=5).read()
            
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:6]
            
            if items:
                for item in items:
                    title = item.find('title').text if item.find('title') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else "#"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    
                    st.markdown(f"### [{title}]({link})")
                    if pub_date:
                        st.caption(f"📅 Publié le : {pub_date[:16]}")
                    st.divider()
            else:
                st.info("Aucune actualité trouvée.")
        except Exception:
            st.error("Impossible de récupérer les flux d'actualités.")

# ==========================================
# 4. SIMULATEUR DCA (PRO)
# ==========================================
elif menu == "Simulateur DCA (Pro)":
    st.title("💰 Simulateur d'Investissement Progressif (DCA)")
    
    if not st.session_state.is_pro:
        st.warning("🔒 Module réservé aux abonnés Emala Pro.")
        st.markdown(f"[👉 **Activer mon accès Pro (9,99 €/mois)**]({STRIPE_PAYMENT_LINK})")
    else:
        c1, c2 = st.columns(2)
        ticker = c1.text_input("Symbole (ex: NVDA, AAPL, BTC-USD)", value="NVDA").strip().upper()
        montant_mensuel = c2.number_input("Versement Mensuel (€/$)", value=200, step=20)

        df = fetch_history(ticker, period="2y")
        if not df.empty and 'Close' in df.columns:
            df_monthly = df['Close'].resample('ME').last().dropna()
            nb_mois = len(df_monthly)
            total_investi = nb_mois * montant_mensuel
            
            parts_cumulees = 0
            historique_portefeuille = []
            
            for price in df_monthly:
                parts_cumulees += montant_mensuel / price
                historique_portefeuille.append(parts_cumulees * price)
                
            valeur_finale = historique_portefeuille[-1]
            profit = valeur_finale - total_investi
            rendement = (profit / total_investi) * 100 if total_investi > 0 else 0

            m1, m2, m3 = st.columns(3)
            with m1: render_metric("Total Investi", f"{round(total_investi, 2)} $")
            with m2: render_metric("Valeur Actuelle", f"{round(valeur_finale, 2)} $")
            status
