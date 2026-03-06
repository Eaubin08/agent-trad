"""
Page 1 — Marché Live
Utilise l'état partagé de session (last_market, history) du moteur principal.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Market — Obsidia", page_icon="📈", layout="wide")

st.title("📈 Marché Live")
st.caption("Données BTC/USDT partagées avec le moteur principal — lancez l'agent depuis **Home**")

# ─── Vérification état session ───────────────────────────────────────────────
if "last_market" not in st.session_state or st.session_state.last_market is None:
    st.warning("⚠️ Aucune donnée de marché disponible. Lancez l'agent depuis la page **Home** (▶ Run).")
    st.info("💡 Allez sur la page **Home**, cliquez **▶ Run**, puis revenez ici.")
    st.stop()

market = st.session_state.last_market
history = st.session_state.get("history", [])

# ─── KPIs marché ─────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    prev_price = history[-2]["price"] if len(history) >= 2 else market.price
    delta_p = market.price - prev_price
    st.metric("💹 Prix BTC", f"${market.price:,.2f}", f"{delta_p:+.2f}")
with col2:
    vol_status = "🔴 Élevée" if market.volatility > 0.5 else "🟢 Normale"
    st.metric("📊 Volatilité", f"{market.volatility:.3f}", vol_status)
with col3:
    er_status = "🔴 Critique" if market.event_risk > 0.88 else "🟢 OK"
    st.metric("⚡ Event Risk", f"{market.event_risk:.3f}", er_status)
with col4:
    obi_label = "🟢 Acheteurs" if market.order_book_imbalance > 0.1 else ("🔴 Vendeurs" if market.order_book_imbalance < -0.1 else "🟡 Équilibré")
    st.metric("📖 OBI", f"{market.order_book_imbalance:+.3f}", obi_label)
with col5:
    st.metric("💧 Spread", f"{market.spread_bps:.1f} bps")

st.divider()

# ─── Indicateurs techniques ───────────────────────────────────────────────────
col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    rsi_color = "🔴" if market.rsi > 70 else "🟢" if market.rsi < 30 else "🟡"
    rsi_label = "Suracheté" if market.rsi > 70 else "Survendu" if market.rsi < 30 else "Neutre"
    st.metric(f"{rsi_color} RSI (14)", f"{market.rsi:.1f}", rsi_label)
with col_b:
    st.metric("📈 SMA 20", f"${market.sma20:,.2f}" if market.sma20 else "—")
with col_c:
    st.metric("📈 SMA 50", f"${market.sma50:,.2f}" if market.sma50 else "—")
with col_d:
    st.metric("😊 Sentiment", f"{market.sentiment_score:+.3f}",
              "Positif" if market.sentiment_score > 0 else "Négatif")

st.divider()

# ─── Graphiques historiques ───────────────────────────────────────────────────
if len(history) >= 2:
    df = pd.DataFrame(history)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("💹 Prix BTC — Historique")
        st.line_chart(df.set_index("cycle")[["price"]], height=220)
    with col_g2:
        st.subheader("📊 RSI (14)")
        st.line_chart(df.set_index("cycle")[["rsi"]], height=220)
        st.caption("🔴 > 70 Suracheté | 🟡 30–70 Neutre | 🟢 < 30 Survendu")

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        st.subheader("📉 Volatilité")
        st.area_chart(df.set_index("cycle")[["volatility"]], height=180)
        st.caption("🔴 > 0.58 = Guard X-108 bloque les trades")
    with col_g4:
        st.subheader("🎯 Score S (Guard X-108)")
        st.line_chart(df.set_index("cycle")[["score_s"]], height=180)
        st.caption(f"Seuil θ_S = {st.session_state.get('guard_threshold', 0.55):.2f}")

else:
    st.info("Lancez l'agent depuis la page **Home** pour accumuler des données de marché.")

st.divider()

# ─── Tableau des derniers cycles ─────────────────────────────────────────────
if history:
    st.subheader("📋 Derniers cycles")
    df_last = pd.DataFrame(history[-20:][::-1])
    decision_icons = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}
    df_last["decision"] = df_last["decision"].map(lambda d: f"{decision_icons.get(d, '⚪')} {d}")
    cols_show = ["cycle", "price", "rsi", "volatility", "decision", "score_s"]
    st.dataframe(df_last[cols_show], use_container_width=True, hide_index=True)

st.divider()

# ─── Données brutes du dernier cycle ─────────────────────────────────────────
with st.expander("🔍 Données brutes du dernier cycle (MarketState)"):
    raw_data = {
        "Prix": f"${market.price:,.2f}",
        "High": f"${market.high:,.2f}" if market.high else "—",
        "Low": f"${market.low:,.2f}" if market.low else "—",
        "Volume": f"{market.volume:,.0f}" if market.volume else "—",
        "Spread (bps)": f"{market.spread_bps:.2f}",
        "OBI": f"{market.order_book_imbalance:+.4f}",
        "Volatilité": f"{market.volatility:.4f}",
        "Event Risk": f"{market.event_risk:.4f}",
        "Sentiment": f"{market.sentiment_score:+.4f}",
        "RSI": f"{market.rsi:.2f}",
        "SMA20": f"${market.sma20:,.2f}" if market.sma20 else "—",
        "SMA50": f"${market.sma50:,.2f}" if market.sma50 else "—",
        "Nb prix historiques": len(market.prices),
    }
    df_raw = pd.DataFrame(list(raw_data.items()), columns=["Métrique", "Valeur"])
    st.dataframe(df_raw, use_container_width=True, hide_index=True)
