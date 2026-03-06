"""
Page 1 — Marché Live
Affiche les données de marché en temps réel (BTC, ETH) avec graphiques natifs Streamlit.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import time

from core.live_market import MockMarketFeed, LiveMarketFeed
from agents.indicators import rsi, macd, atr, sma, realized_volatility

st.set_page_config(page_title="Market — Obsidia", page_icon="📈", layout="wide")

st.title("📈 Marché Live")
st.caption("Données BTC/USDT en temps réel (Binance) ou simulées")

# ─── Initialisation ──────────────────────────────────────────────────────────
if "market_history" not in st.session_state:
    st.session_state.market_history = []
if "market_running" not in st.session_state:
    st.session_state.market_running = False

sim_mode = st.session_state.get("sim_mode", True)
drift_bias = st.session_state.get("drift_bias", 0.0)
vol_mult = st.session_state.get("vol_mult", 1.0)

# ─── Contrôles ───────────────────────────────────────────────────────────────
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 4])
with col_ctrl1:
    if st.button("▶ Démarrer flux", type="primary", use_container_width=True):
        st.session_state.market_running = True
with col_ctrl2:
    if st.button("⏹ Arrêter", use_container_width=True):
        st.session_state.market_running = False
with col_ctrl3:
    refresh_rate = st.slider("Vitesse (secondes)", 0.5, 5.0, 1.0, 0.5)

st.divider()

# ─── Récupération d'un tick ───────────────────────────────────────────────────
def fetch_tick():
    if sim_mode:
        feed = MockMarketFeed(drift_bias=drift_bias, volatility_multiplier=vol_mult)
    else:
        feed = LiveMarketFeed()
    m = feed.get_state()
    if m is None:
        m = MockMarketFeed().get_state()
    return m

if st.session_state.market_running or not st.session_state.market_history:
    m = fetch_tick()
    st.session_state.market_history.append({
        "time": len(st.session_state.market_history),
        "price": round(m.price, 2),
        "volume": round(m.volume, 0),
        "rsi": round(m.rsi, 1),
        "volatility": round(m.volatility * 100, 2),
        "spread": round(m.spread, 4),
    })
    if len(st.session_state.market_history) > 300:
        st.session_state.market_history = st.session_state.market_history[-300:]

# ─── Affichage des métriques actuelles ───────────────────────────────────────
if st.session_state.market_history:
    latest = st.session_state.market_history[-1]
    prev = st.session_state.market_history[-2] if len(st.session_state.market_history) > 1 else latest

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        delta_price = latest["price"] - prev["price"]
        st.metric("💹 BTC/USDT", f"${latest['price']:,.2f}", f"{delta_price:+.2f}")
    with c2:
        rsi_val = latest["rsi"]
        rsi_status = "🔴 Suracheté" if rsi_val > 70 else ("🟢 Survendu" if rsi_val < 30 else "🟡 Neutre")
        st.metric("📊 RSI(14)", f"{rsi_val:.1f}", rsi_status)
    with c3:
        st.metric("📉 Volatilité", f"{latest['volatility']:.2f}%")
    with c4:
        st.metric("📦 Volume", f"{latest['volume']:,.0f}")
    with c5:
        st.metric("↔️ Spread", f"{latest['spread']:.4f}")

    st.divider()

    # ─── Graphiques ──────────────────────────────────────────────────────────
    df = pd.DataFrame(st.session_state.market_history)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("💹 Prix BTC/USDT")
        if len(df) >= 2:
            st.line_chart(df.set_index("time")["price"], height=250, color="#58a6ff")
        else:
            st.info("Accumulation de données...")

    with col_g2:
        st.subheader("📊 RSI(14)")
        if len(df) >= 2:
            df_rsi = df.set_index("time")[["rsi"]].copy()
            st.line_chart(df_rsi, height=250, color="#f0883e")
            # Zones RSI
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown("🔴 **>70** Suracheté")
            with col_r2:
                st.markdown("🟡 **30-70** Neutre")
            with col_r3:
                st.markdown("🟢 **<30** Survendu")

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.subheader("📉 Volatilité réalisée (%)")
        if len(df) >= 2:
            st.area_chart(df.set_index("time")["volatility"], height=200, color="#da3633")

    with col_g4:
        st.subheader("📦 Volume")
        if len(df) >= 2:
            st.bar_chart(df.set_index("time")["volume"], height=200, color="#2ea043")

    st.divider()

    # ─── Tableau des derniers ticks ──────────────────────────────────────────
    st.subheader("📋 Derniers ticks")
    df_display = df.tail(20)[::-1].copy()
    df_display.columns = ["Tick", "Prix ($)", "Volume", "RSI", "Volatilité (%)", "Spread"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# Auto-refresh si running
if st.session_state.market_running:
    time.sleep(refresh_rate)
    st.rerun()
