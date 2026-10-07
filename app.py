import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

st.set_page_config(page_title="Emala Finance Pro", page_icon="⚡", layout="wide")

# Barre latérale
st.sidebar.title("⚡ Emala Finance Pro")
ticker = st.sidebar.text_input("Symbole principal", value="NVDA").upper().strip()
period = st.sidebar.selectbox("Horizon temporel", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)

st.sidebar.subheader("Indicateurs Techniques")
show_sma = st.sidebar.checkbox("Moyennes Mobiles (SMA 20/50)", value=True)
show_bollinger = st.sidebar.checkbox("Bandes de Bollinger", value=False)
show_rsi = st.sidebar.checkbox("RSI (14)", value=True)
show_macd = st.sidebar.checkbox("MACD", value=False)

if ticker:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        info = stock.info

        if df.empty:
            st.error("Aucune donnée disponible pour ce symbole.")
        else:
            # Métriques principales
            st.title(f"{info.get('longName', ticker)} ({ticker})")
            
            price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2] if len(df) > 1 else price
            pct_change = ((price - prev_price) / prev_price) * 100

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Prix Actuel", f"${price:.2f}", f"{pct_change:+.2f}%")
            col2.metric("Plus Haut (Période)", f"${df['High'].max():.2f}")
            col3.metric("Plus Bas (Période)", f"${df['Low'].min():.2f}")
            
            market_cap = info.get('marketCap')
            cap_str = f"${market_cap/1e12:.2f} T" if market_cap and market_cap >= 1e12 else (f"${market_cap/1e9:.2f} B" if market_cap and market_cap >= 1e9 else "N/A")
            col4.metric("Capitalisation", cap_str)
            col5.metric("Objectif Moyen", f"${info.get('targetMeanPrice', 'N/A')}")

            st.divider()

            # Onglets de l'application
            tab_tech, tab_fund, tab_comp, tab_dca, tab_news = st.tabs([
                "📊 Analyse Technique", 
                "🏢 Fondamentaux & Analystes", 
                "⚖️ Comparateur", 
                "💰 Simulateur DCA", 
                "📰 Actualités"
            ])

            # ONGLET 1 : ANALYSE TECHNIQUE
            with tab_tech:
                if show_sma:
                    df['SMA_20'] = df['Close'].rolling(20).mean()
                    df['SMA_50'] = df['Close'].rolling(50).mean()
                
                if show_bollinger:
                    sma20 = df['Close'].rolling(20).mean()
                    std20 = df['Close'].rolling(20).std()
                    df['BB_Upper'] = sma20 + (std20 * 2)
                    df['BB_Lower'] = sma20 - (std20 * 2)
                
                if show_rsi:
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss
                    df['RSI'] = 100 - (100 / (1 + rs))

                if show_macd:
                    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
                    df['MACD'] = exp1 - exp2
                    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

                # Configuration dynamique des graphiques
                rows = 2
                row_heights = [0.7, 0.3]
                if show_rsi and show_macd:
                    rows = 4
                    row_heights = [0.5, 0.15, 0.175, 0.175]
                elif show_rsi or show_macd:
                    rows = 3
                    row_heights = [0.6, 0.2, 0.2]

                fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

                # Prix & Chandeliers
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Prix"), row=1, col=1)

                if show_sma:
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="SMA 20", line=dict(color='orange', width=1)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name="SMA 50", line=dict(color='limegreen', width=1)), row=1, col=1)

                if show_bollinger:
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name="BB Haut", line=dict(color='gray', dash='dash')), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name="BB Bas", line=dict(color='gray', dash='dash'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

                # Volume
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='rgba(0,150,255,0.5)'), row=2, col=1)

                curr_row = 3
                if show_rsi:
                    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI (14)", line=dict(color='purple')), row=curr_row, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr_row, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr_row, col=1)
                    curr_row += 1

                if show_macd:
                    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD", line=dict(color='cyan')), row=curr_row, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name="Signal", line=dict(color='magenta')), row=curr_row, col=1)
                    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name="Hist", marker_color='gray'), row=curr_row, col=1)

                fig.update_layout(template="plotly_dark", height=750, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

                csv = df.to_csv().encode('utf-8')
                st.download_button("📥 Télécharger l'historique en CSV", data=csv, file_name=f"{ticker}_historique.csv", mime="text/csv")

            # ONGLET 2 : FONDAMENTAUX ET ANALYSTES
            with tab_fund:
                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    st.subheader("🏢 Fiche Entreprise")
                    st.write(f"**Secteur :** {info.get('sector', 'N/A')}")
                    st.write(f"**Industrie :** {info.get('industry', 'N/A')}")
                    st.write(f"**P/E Ratio (Forward) :** {info.get('forwardPE', 'N/A')}")
                    st.write(f"**Rendement Dividende :** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "**Rendement Dividende :** N/A")
                    st.write(f"**Bêta (Volatilité) :** {info.get('beta', 'N/A')}")
                    st.markdown("---")
                    st.write("**Description :**")
                    st.write(info.get('longBusinessSummary', 'Aucune description disponible.'))

                with col_f2:
                    st.subheader("🎯 Avis des Analystes")
                    target_low = info.get('targetLowPrice')
                    target_mean = info.get('targetMeanPrice')
                    target_high = info.get('targetHighPrice')
                    rec = info.get('recommendationKey', 'N/A').upper().replace('_', ' ')

                    st.metric("Consensus", rec)

                    if target_mean and target_low and target_high:
                        fig_target = go.Figure()
                        fig_target.add_trace(go.Bar(
                            x=['Min', 'Moyen', 'Actuel', 'Max'],
                            y=[target_low, target_mean, price, target_high],
                            marker_color=['#ff4b4b', '#1c83e1', '#00d4b1', '#00c04b']
                        ))
                        fig_target.update_layout(title="Objectifs de prix ($)", template="plotly_dark", height=300)
                        st.plotly_chart(fig_target, use_container_width=True)

            # ONGLET 3 : COMPARATEUR
            with tab_comp:
                st.subheader("⚖️ Comparer la performance relative (%)")
                others = st.text_input("Ajouter d'autres symboles (séparés par une virgule)", value="AAPL, MSFT, GOOGL")
                comp_tickers = [t.strip().upper() for t in others.split(",") if t.strip()]
                all_tickers = list(dict.fromkeys([ticker] + comp_tickers))

                if st.button("Lancer la comparaison"):
                    data_comp = yf.download(all_tickers, period=period)['Close']
                    if not data_comp.empty:
                        norm_data = (data_comp / data_comp.iloc[0] - 1) * 100
                        fig_comp = px.line(norm_data, title=f"Performance comparée (%) - Horizon {period}")
                        fig_comp.update_layout(template="plotly_dark", height=500, yaxis_title="Performance (%)")
                        st.plotly_chart(fig_comp, use_container_width=True)

            # ONGLET 4 : SIMULATEUR DCA
            with tab_dca:
                st.subheader("💰 Simulateur d'Investissement Régulier (DCA)")
                monthly_inv = st.number_input("Montant investi par mois ($)", value=100, min_value=10, step=10)
                
                monthly_df = df['Close'].resample('ME').last()
                if len(monthly_df) > 1:
                    total_invested = len(monthly_df) * monthly_inv
                    total_shares = (monthly_inv / monthly_df).sum()
                    final_value = total_shares * price
                    profit = final_value - total_invested
                    roi = (profit / total_invested) * 100

                    st.markdown(f"Résultat d'un investissement de **${monthly_inv}/mois** sur **{len(monthly_df)} mois** :")
                    c_dca1, c_dca2, c_dca3 = st.columns(3)
                    c_dca1.metric("Total Investi", f"${total_invested:,.2f}")
                    c_dca2.metric("Valeur Actuelle", f"${final_value:,.2f}", f"{roi:+.2f}%")
                    c_dca3.metric("Gain / Perte", f"${profit:,.2f}")
                else:
                    st.info("Sélectionne un horizon d'au moins 1 an pour simuler un investissement mensuel.")

            # ONGLET 5 : ACTUALITÉS
            with tab_news:
                st.subheader("📰 Fil d'actualités")
                news_list = stock.news
                if news_list:
                    for item in news_list[:8]:
                        title = item.get('title') or 'Titre indisponible'
                        link = item.get('link') or '#'
                        publisher = item.get('publisher') or 'Source inconnue'
                        st.markdown(f"🔹 [{title}]({link})")
                        st.caption(f"Source : {publisher}")
                        st.write("---")
                else:
                    st.info("Aucune actualité récente disponible.")

    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
