import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Config de la page
st.set_page_config(
    page_title="Emala Finance Pro",
    page_icon="⚡",
    layout="wide"
)

# Style CSS personnalisé
st.markdown("""
    <style>
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE CACHE & CALCULS ---
@st.cache_data(ttl=600)
def load_data(ticker, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    info = stock.info
    return df, info

@st.cache_data(ttl=1800)
def load_news(ticker):
    return yf.Ticker(ticker).news

def compute_indicators(df):
    # SMA
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    
    # RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    
    return df

def fmt_num(val, unit=""):
    if val is None or pd.isna(val):
        return "N/A"
    if abs(val) >= 1e12:
        return f"{val/1e12:.2f} T {unit}".strip()
    if abs(val) >= 1e9:
        return f"{val/1e9:.2f} B {unit}".strip()
    if abs(val) >= 1e6:
        return f"{val/1e6:.2f} M {unit}".strip()
    return f"{val:,.2f} {unit}".replace(",", " ").strip()


# --- SIDEBAR DE CONFIGURATION ---
st.sidebar.title("⚡ Emala Finance")
ticker = st.sidebar.text_input("Symbole d'action", value="NVDA").upper().strip()
period = st.sidebar.selectbox(
    "Horizon temporel",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=3
)

st.sidebar.subheader("Indicateurs techniques")
show_sma = st.sidebar.checkbox("Moyennes Mobiles (SMA 20/50)", value=True)
show_rsi = st.sidebar.checkbox("RSI (14)", value=True)
show_macd = st.sidebar.checkbox("MACD", value=False)
chart_type = st.sidebar.radio("Type de graphique", ["Chandeliers", "Ligne"])

# --- APPLICATION PRINCIPALE ---
if ticker:
    try:
        with st.spinner("Chargement des données de marché..."):
            df, info = load_data(ticker, period)
            
        if df.empty:
            st.error(f"Impossible de trouver des données pour '{ticker}'. Vérifie le symbole.")
        else:
            df = compute_indicators(df)
            company_name = info.get("longName", ticker)
            currency = info.get("currency", "USD")
            curr_sym = "€" if currency == "EUR" else "$"

            # En-tête
            st.title(f"{company_name} (`{ticker}`)")
            
            # Barres d'onglets
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Analyse Technique", 
                "🏢 Fondamentaux", 
                "📰 Actualités", 
                "⚖️ Comparateur"
            ])

            # ================= TAB 1 : GRAPHIC & TECHNIQUE =================
            with tab1:
                last_price = df["Close"].iloc[-1]
                prev_price = df["Close"].iloc[-2] if len(df) > 1 else last_price
                diff = last_price - prev_price
                pct = (diff / prev_price) * 100

                # KPI Top
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("Prix Actuel", f"{last_price:.2f} {curr_sym}", f"{pct:+.2f}%")
                k2.metric("Plus Haut (Période)", f"{df['High'].max():.2f} {curr_sym}")
                k3.metric("Plus Bas (Période)", f"{df['Low'].min():.2f} {curr_sym}")
                k4.metric("Volume Récents", fmt_num(df["Volume"].iloc[-1]))
                k5.metric("Capitalisation", fmt_num(info.get("marketCap"), curr_sym))

                # Structure dynamique du graphique Plotly
                rows = 2
                row_heights = [0.7, 0.3]
                if show_rsi and show_macd:
                    rows = 4
                    row_heights = [0.5, 0.2, 0.15, 0.15]
                elif show_rsi or show_macd:
                    rows = 3
                    row_heights = [0.6, 0.2, 0.2]

                fig = make_subplots(
                    rows=rows, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.03,
                    row_heights=row_heights
                )

                # 1. Prix
                if chart_type == "Chandeliers":
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df["Open"], high=df["High"],
                        low=df["Low"], close=df["Close"], name="Prix"
                    ), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df["Close"], mode="lines",
                        name="Prix de Clôture", line=dict(color="#00F0FF", width=2)
                    ), row=1, col=1)

                if show_sma:
                    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", line=dict(color="orange", width=1.2)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line=dict(color="#39FF14", width=1.2)), row=1, col=1)

                # 2. Volume
                colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df["Close"], df["Open"])]
                fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=colors), row=2, col=1)

                # 3. RSI / MACD
                curr_row = 3
                if show_rsi:
                    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI (14)", line=dict(color="purple")), row=curr_row, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr_row, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr_row, col=1)
                    curr_row += 1

                if show_macd:
                    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="blue")), row=curr_row, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal", line=dict(color="orange")), row=curr_row, col=1)

                fig.update_layout(
                    template="plotly_dark",
                    height=700,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_rangeslider_visible=False,
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)

            # ================= TAB 2 : FONDAMENTAUX =================
            with tab2:
                st.subheader("Profil de l'entreprise")
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Secteur :** {info.get('sector', 'N/A')}")
                c2.write(f"**Industrie :** {info.get('industry', 'N/A')}")
                c3.write(f"**Pays :** {info.get('country', 'N/A')}")
                c4.write(f"**Employés :** {fmt_num(info.get('fullTimeEmployees'))}")

                st.divider()
                st.subheader("Ratios Financiers Clés")
                
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("PER (Trailing P/E)", fmt_num(info.get("trailingPE")))
                f2.metric("PER Projeté (Forward P/E)", fmt_num(info.get("forwardPE")))
                f3.metric("Ratio PEG", fmt_num(info.get("pegRatio")))
                f4.metric("Prix / Valeur comptable", fmt_num(info.get("priceToBook")))

                f5, f6, f7, f8 = st.columns(4)
                f5.metric("Marge Nette", f"{info.get('profitMargins', 0)*100:.2f} %" if info.get('profitMargins') else "N/A")
                f6.metric("Rentabilité des fonds propres (ROE)", f"{info.get('returnOnEquity', 0)*100:.2f} %" if info.get('returnOnEquity') else "N/A")
                f7.metric("Volatilité (Bêta)", fmt_num(info.get("beta")))
                f8.metric("Rendement du Dividende", f"{info.get('dividendYield', 0)*100:.2f} %" if info.get('dividendYield') else "N/A")

                st.divider()
                with st.expander("📄 Description complète du business"):
                    st.write(info.get("longBusinessSummary", "Aucune description disponible."))

            # ================= TAB 3 : ACTUALITÉS =================
            with tab3:
                st.subheader(f"Dernières actualités sur {company_name}")
                news = load_news(ticker)
                if not news:
                    st.info("Aucune actualité disponible pour le moment.")
                else:
                    for item in news[:8]:
                        # yfinance a parfois des structures dict variables selon la version
                        title = item.get("title") or item.get("content", {}).get("title")
                        link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url")
                        publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName", "Presse")
                        
                        if title and link:
                            st.markdown(f"##### [{title}]({link})")
                            st.caption(f"Source : **{publisher}**")
                            st.write("---")

            # ================= TAB 4 : COMPARATEUR =================
            with tab4:
                st.subheader("Comparer la performance relative")
                compare_ticker = st.text_input("Symbole à comparer (ex: AAPL, MSFT, ^GSPC)", value="AAPL").upper().strip()
                
                if compare_ticker:
                    df_comp, info_comp = load_data(compare_ticker, period)
                    if not df_comp.empty:
                        # Normalisation à 100% au début de la période
                        norm_df1 = (df["Close"] / df["Close"].iloc[0]) * 100
                        norm_df2 = (df_comp["Close"] / df_comp["Close"].iloc[0]) * 100

                        fig_comp = go.Figure()
                        fig_comp.add_trace(go.Scatter(x=df.index, y=norm_df1, name=ticker, line=dict(width=2)))
                        fig_comp.add_trace(go.Scatter(x=df_comp.index, y=norm_df2, name=compare_ticker, line=dict(width=2)))
                        
                        fig_comp.update_layout(
                            template="plotly_dark",
                            title="Base 100 (Évolution en % sur la période)",
                            yaxis_title="Performance relative",
                            height=500
                        )
                        st.plotly_chart(fig_comp, use_container_width=True)

    except Exception as e:
        st.error(f"Une erreur est survenue lors de l'exécution : {e}")