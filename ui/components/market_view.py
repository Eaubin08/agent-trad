"""
market_view.py — Vue marché : prix, volume, volatilité, mini-chart.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from agents.indicators import MarketState


def render_market_view(state: MarketState) -> None:
    st.subheader("📊 Market Data — BTC/USDT")

    col1, col2, col3, col4 = st.columns(4)
    price = state.prices[-1] if state.prices else 0.0
    prev  = state.prices[-2] if len(state.prices) >= 2 else price
    delta = price - prev

    col1.metric("Prix BTC", f"${price:,.2f}", f"{delta:+.2f}")
    col2.metric("Volume", f"{state.volumes[-1]:,.0f}" if state.volumes else "—")
    col3.metric("Volatilité", f"{state.volatility:.4f}")
    col4.metric("Spread (bps)", f"{state.spreads_bps[-1]:.1f}" if state.spreads_bps else "—")

    # Mini-chart prix
    if len(state.prices) >= 5:
        prices = list(state.prices)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=prices,
            mode="lines",
            line=dict(color="#00d4aa", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,212,170,0.08)",
            name="Prix"
        ))
        fig.update_layout(
            height=160,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")
