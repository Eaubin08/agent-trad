"""
agent_brain.py — Vue Agent Brain : RSI, MACD, ATR, volatilité, trend par agent.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from agents.indicators import MarketState, rsi, macd, atr, realized_volatility, sma


def render_agent_brain(state: MarketState) -> None:
    st.subheader("🧠 Agent Brain — Indicateurs techniques en temps réel")

    prices = list(state.prices)
    volumes = list(state.volumes) if state.volumes else []

    if len(prices) < 30:
        st.warning("Pas assez de données pour afficher les indicateurs (minimum 30 points).")
        return

    # Calcul des indicateurs
    rsi_val  = rsi(prices)
    macd_val, signal_val, hist_val = macd(prices)
    atr_val  = atr(prices, prices, prices)  # simplifié : high=low=close
    vol_val  = realized_volatility(prices)
    sma20    = sma(prices, 20)
    sma50    = sma(prices, 50) if len(prices) >= 50 else sma20
    trend    = "↑ HAUSSIER" if sma20 > sma50 else "↓ BAISSIER"
    trend_color = "#00d4aa" if sma20 > sma50 else "#ff4b6e"

    # Métriques rapides
    c1, c2, c3, c4, c5 = st.columns(5)
    rsi_color = "#ff4b6e" if rsi_val > 70 else ("#00d4aa" if rsi_val < 30 else "#f5a623")
    c1.metric("RSI (14)", f"{rsi_val:.1f}", help="Suracheté >70 | Survendu <30")
    c2.metric("MACD", f"{macd_val:.4f}", f"Signal: {signal_val:.4f}")
    c3.metric("ATR", f"{atr_val:.2f}", help="Average True Range — volatilité de prix")
    c4.metric("Vol. réalisée", f"{vol_val:.4f}")
    c5.metric("Tendance", trend)

    # Graphiques
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("Prix + SMA", "RSI (14)", "MACD"),
        vertical_spacing=0.08,
    )

    x = list(range(len(prices)))

    # Prix + SMA
    fig.add_trace(go.Scatter(
        x=x, y=prices,
        mode="lines", name="Prix",
        line=dict(color="#00d4aa", width=1.5),
    ), row=1, col=1)

    sma20_series = [sma(prices[:i+1], 20) for i in range(len(prices))]
    fig.add_trace(go.Scatter(
        x=x, y=sma20_series,
        mode="lines", name="SMA20",
        line=dict(color="#f5a623", width=1, dash="dot"),
    ), row=1, col=1)

    # RSI
    rsi_series = [rsi(prices[:i+1]) if i >= 14 else 50.0 for i in range(len(prices))]
    fig.add_trace(go.Scatter(
        x=x, y=rsi_series,
        mode="lines", name="RSI",
        line=dict(color="#a78bfa", width=1.5),
    ), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff4b6e", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00d4aa", row=2, col=1)

    # MACD histogram
    macd_hist = []
    for i in range(len(prices)):
        if i >= 26:
            m, s, h = macd(prices[:i+1])
            macd_hist.append(h)
        else:
            macd_hist.append(0.0)

    colors_hist = ["#00d4aa" if v >= 0 else "#ff4b6e" for v in macd_hist]
    fig.add_trace(go.Bar(
        x=x, y=macd_hist,
        name="MACD Hist",
        marker_color=colors_hist,
    ), row=3, col=1)

    fig.update_layout(
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc"),
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    for i in range(1, 4):
        fig.update_xaxes(showgrid=False, row=i, col=1)
        fig.update_yaxes(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            row=i, col=1
        )

    st.plotly_chart(fig, width="stretch")
