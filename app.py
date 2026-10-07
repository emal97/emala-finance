import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import re

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="Emala Finance Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE CSS PREMIUM (SAAS DARK MODE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    
    /* Customisation des métriques natives Streamlit */
    div[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; color: #58A6FF; }
    div[data-testid="stMetricDelta"] { font-size: 1.1rem; font-weight: 600; }
    
    /* Customisation de la sidebar */
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
</style>
""", unsafe_allow_html=True)

# --- SESSION & AUTHENTIFICATION STRIPE ---
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

# --- NETTOYAGE AUTOMATIQUE DU TICKER ---
TICKER_MAP = {
    "NVIDIA": "NVDA", "NVIDIAC": "NVDA", "APPLE": "AAPL", 
    "MICROSOFT": "MSFT", "TESLA": "TSLA", "GOOGLE": "GOOGL", "AMAZON": "AMZN",
    "BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"
}

def clean_ticker(user_input):
    clean = re.sub(r'[^a-zA-Z0-9\.\-]', '', str(user_input)).strip().upper()
    return TICKER_MAP.get(clean, clean)

# --- APPELS RÉSEAU EN CACHE (ANTI-PLANTAGE) ---
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
def fetch_fundamentals(ticker):
    price_val, mcap_val, per_val, div_val = "N/A", "N/A", "N/A", "N/A"
    summary_txt = None
    
    try:
        stock = yf.Ticker(ticker)
        fast = stock.fast_info
        price = getattr(fast, 'last_price', None)
        currency = getattr(fast, 'currency', 'USD')
        if price: price_val = f"{round(price, 2)} {currency}"
        mcap = getattr(fast, 'market_cap', None)
        if mcap: mcap_val = f"{round(mcap / 1e9, 2)} B {currency}"
    except Exception:
        pass

    try:
        url_qs = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(ticker)}?modules=summaryDetail,defaultKeyStatistics"
        req = urllib.request.Request(url_qs, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=4)
        qs_data = json.loads(res.read().decode('utf-8'))
        result = qs_data.get('quoteSummary', {}).get('result', [])
        if result:
            sd = result[0].get('summaryDetail', {})
            ks = result[0].get('defaultKeyStatistics', {})
            pe_raw = sd.get('trailingPE', {}).get('raw') or ks.get('trailingPE', {}).get('raw')
            if pe_raw: per_val = f"{round(pe_raw, 2)}"
            div_raw = sd.get('dividendYield', {}).get('raw')
            if div_raw is not None: div_val = f"{round(div_raw * 100, 2)}%"
            else: div_val = "0,0%"
    except Exception:
        pass

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

    return price_val, per_val, div_val, mcap_val, summary_txt

# ==========================================
# 1. ANALYSE TECHNIQUE (GRAPHIQUES PRO PLOTLY)
# ==========================================
if menu == "Analyse Technique":
    st.title("📈 Analyse Technique Avancée")
    
    col_input, col_period = st.columns([3, 1])
    raw_input = col_input.text_input("Symbole (ex: NVDA, AAPL, BTC-USD)", value="NVDA")
    period = col_period.selectbox("Horizon", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    ticker = clean_ticker(raw_input)

    if ticker:
        df = fetch_history(ticker, period=period)
        if not df.empty and 'Close' in df.columns:
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, 
                vertical_spacing=0.05, subplot_titles=(f"Cours & Moyennes Mobiles — {ticker}", "RSI (14)"),
                row_width=[0.25, 0.75]
            )

            # Chandeliers Japonais
            if 'Open' in df.columns and 'High' in df.columns:
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prix"
                ), row=1, col=1)
            else:
                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name="Prix", line=dict(color='#58A6FF')), row=1, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], mode='lines', name="EMA 20", line=dict(color='#E3B341', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], mode='lines', name="EMA 50", line=dict(color='#A371F7', width=1.5)), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name="RSI", line=dict(color='#F0883E', width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#F85149", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#3FB950", row=2, col=1)

            fig.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,27,34,0.8)",
                xaxis_rangeslider_visible=False, height=650, margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Données graphiques indisponibles pour ce symbole.")

# ==========================================
# 2. ANALYSE FONDAMENTALE
# ==========================================
elif menu == "Analyse Fondamentale":
    st.title("📊 Analyse Fondamentale")
    raw_input = st.text_input("Symbole ou Nom de l'entreprise", value="NVDA")
    ticker = clean_ticker(raw_input)
    
    if ticker:
        price_val, per_val, div_val, mcap_val, summary_txt = fetch_fundamentals(ticker)
        st.caption(f"Ticker identifié : **{ticker}**")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", price_val)
        c2.metric("P/E Ratio (PER)", per_val)
        c3.metric("Rendement Dividende", div_val)
        c4.metric("Capitalisation", mcap_val)

        st.subheader("📋 Profil de l'entreprise")
        if summary_txt:
            st.write(summary_txt)
        else:
            st.warning("Aucune description disponible pour ce symbole.")

# ==========================================
# 3. ACTUALITÉS
# ==========================================
elif menu == "Actualités":
    st.title("📰 Flux d'Actualités")
    raw_input = st.text_input("Sujet ou Ticker", value="NVDA")
    ticker = clean_ticker(raw_input)
    
    if ticker:
        try:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(ticker + ' bourse finance')}&hl=fr&gl=FR&ceid=FR:fr"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=5).read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:6]
            
            if items:
                for item in items:
                    t = item.find('title').text if item.find('title') is not None else ""
                    l = item.find('link').text if item.find('link') is not None else "#"
                    d = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    st.markdown(f"### [{t}]({l})")
                    if d: st.caption(f"📅 Publié le : {d[:16]}")
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
        raw_input = c1.text_input("Symbole (ex: NVDA, BTC-USD)", value="NVDA")
        montant_mensuel = c2.number_input("Versement Mensuel (€/$)", value=200, step=20)
        ticker = clean_ticker(raw_input)

        df = fetch_history(ticker, period="2y")
        if not df.empty and 'Close' in df.columns:
            df_monthly = df['Close'].resample('ME').last().dropna()
            
            total_investi = 0
            parts_cumulees = 0
            historique_port = []
            historique_inv = []
            
            for price in df_monthly:
                total_investi += montant_mensuel
                parts_cumulees += montant_mensuel / price
                historique_port.append(parts_cumulees * price)
                historique_inv.append(total_investi)
                
            valeur_finale = historique_port[-1] if historique_port else 0
            profit = valeur_finale - total_investi
            rendement = (profit / total_investi) * 100 if total_investi > 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Investi", f"{round(total_investi, 2)} $")
            m2.metric("Valeur Actuelle", f"{round(valeur_finale, 2)} $")
            m3.metric("Performance Nette", f"{round(profit, 2)} $", f"{round(rendement, 2)} %")

            fig_dca = go.Figure()
            fig_dca.add_trace(go.Scatter(x=df_monthly.index, y=historique_port, mode='lines+markers', name="Portefeuille", line=dict(color='#3FB950', width=3)))
            fig_dca.add_trace(go.Scatter(x=df_monthly.index, y=historique_inv, mode='lines', name="Total Investi", line=dict(color='#8B949E', dash='dash')))
            
            fig_dca.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,27,34,0.8)",
                height=450, margin=dict(l=10, r=10, t=30, b=10), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
            )
            st.plotly_chart(fig_dca, use_container_width=True)
        else:
            st.error("Données historiques insuffisantes pour simuler le DCA.")

# ==========================================
# 5. COMPARATEUR MULTI-ACTIONS (PRO)
# ==========================================
elif menu == "Comparateur (Pro)":
    st.title("⚔️ Comparateur de Performance Relative")
    
    if not st.session_state.is_pro:
        st.warning("🔒 Module réservé aux abonnés Emala Pro.")
        st.markdown(f"[👉 **Activer mon accès Pro**]({STRIPE_PAYMENT_LINK})")
    else:
        tickers_input = st.text_input("Actifs à comparer (séparés par des virgules)", value="NVDA, AAPL, MSFT, TSLA")
        tickers = [clean_ticker(t) for t in tickers_input.split(",") if t.strip()]

        if tickers:
            fig_comp = go.Figure()
            for t in tickers:
                df = fetch_history(t, period="1y")
                if not df.empty and 'Close' in df.columns:
                    perf_base100 = (df['Close'] / df['Close'].iloc[0]) * 100
                    fig_comp.add_trace(go.Scatter(x=df.index, y=perf_base100, mode='lines', name=t))

            fig_comp.update_layout(
                title="Évolution comparée sur 1 an (Base 100)",
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,27,34,0.8)",
                height=500, yaxis_title="Performance (%)"
            )
            st.plotly_chart(fig_comp, use_container_width=True)
