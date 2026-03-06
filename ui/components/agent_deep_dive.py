"""
Obsidia x ERC-8004 — Agent Deep Dive Component
Vue détaillée du raisonnement de chaque agent : données brutes, formule, graphique.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agents.indicators import (
    MarketState, atr, bollinger, ema, macd, rsi, sma, zscore, realized_volatility
)
from agents.registry import AgentVote


# ── Descriptions pédagogiques de chaque agent ──────────────────────────────

AGENT_DESCRIPTIONS = {
    "MarketDataAgent": {
        "role": "Observe le changement de prix entre deux périodes consécutives.",
        "logic": "Si le prix monte de plus de 0.1% → BUY. S'il baisse de plus de 0.1% → SELL. Sinon → HOLD.",
        "formula": "signal = BUY si (prix_t - prix_t-1) / prix_t-1 > 0.001",
        "chart_type": "price_change",
        "emoji": "📡",
    },
    "LiquidityAgent": {
        "role": "Surveille le volume et le spread pour détecter les conditions de liquidité.",
        "logic": "Volume élevé + spread serré → BUY (marché liquide). Volume faible ou spread large → SELL.",
        "formula": "signal = BUY si volume > avg20 ET spread_bps < avg_spread",
        "chart_type": "volume",
        "emoji": "💧",
    },
    "VolatilityAgent": {
        "role": "Compare la volatilité court terme (20 périodes) vs long terme (60 périodes).",
        "logic": "Si la volatilité récente est 30% au-dessus de la moyenne → SELL (risque). Si elle est 15% en dessous → BUY (calme).",
        "formula": "signal = SELL si rv20 > rv60 × 1.30 | BUY si rv20 < rv60 × 0.85",
        "chart_type": "volatility",
        "emoji": "🌊",
    },
    "MacroAgent": {
        "role": "Évalue le risque macro-économique via un score d'événement.",
        "logic": "Score de risque > 0.7 → SELL (danger macro). Score < 0.3 → BUY (environnement favorable).",
        "formula": "signal = SELL si event_risk > 0.70 | BUY si event_risk < 0.30",
        "chart_type": "event_risk",
        "emoji": "🌍",
    },
    "MomentumAgent": {
        "role": "Détecte la tendance directionnelle sur 5 périodes, confirmée par le RSI.",
        "logic": "Rendement positif sur 5 périodes ET RSI < 75 (non suracheté) → BUY. Rendement négatif ET RSI > 25 → SELL.",
        "formula": "ret5 = (prix_t - prix_t-5) / prix_t-5 | BUY si ret5 > 0 ET rsi14 < 75",
        "chart_type": "rsi",
        "emoji": "🚀",
    },
    "MeanReversionAgent": {
        "role": "Cherche les prix extrêmes par rapport à la moyenne mobile (Bollinger Bands).",
        "logic": "Prix sous la bande inférieure ou Z-score < -2 → BUY (rebond attendu). Prix au-dessus de la bande supérieure → SELL.",
        "formula": "BUY si prix < BB_lower ou zscore20 < -2.0 | SELL si prix > BB_upper",
        "chart_type": "bollinger",
        "emoji": "↩️",
    },
    "BreakoutAgent": {
        "role": "Détecte les cassures de niveaux de support et résistance sur 20 périodes.",
        "logic": "Prix au-dessus du plus haut des 20 dernières périodes → BUY (breakout). Prix sous le plus bas → SELL.",
        "formula": "BUY si prix > max(highs[-20:]) | SELL si prix < min(lows[-20:])",
        "chart_type": "breakout",
        "emoji": "💥",
    },
    "PatternAgent": {
        "role": "Reconnaît les séquences de prix haussières ou baissières sur 5 périodes.",
        "logic": "4 hausses consécutives + MACD histogramme positif → BUY. 4 baisses consécutives → SELL.",
        "formula": "BUY si rises >= 4 ET macd_hist > 0 | SELL si drops >= 4",
        "chart_type": "macd",
        "emoji": "🔍",
    },
    "SentimentAgent": {
        "role": "Analyse le sentiment de marché (proxy via variation de prix normalisée).",
        "logic": "Score de sentiment > 0.20 → BUY. Score < -0.20 → SELL.",
        "formula": "signal = BUY si sentiment_score > 0.20 | SELL si < -0.20",
        "chart_type": "sentiment",
        "emoji": "😊",
    },
    "EventAgent": {
        "role": "Réagit aux événements de marché à fort impact (news, macro).",
        "logic": "Risque d'événement > 0.65 → SELL (prudence). Risque < 0.25 → BUY (calme).",
        "formula": "SELL si event_risk > 0.65 | BUY si event_risk < 0.25",
        "chart_type": "event_risk",
        "emoji": "⚡",
    },
    "CorrelationAgent": {
        "role": "Vérifie la cohérence entre le mouvement de l'actif et BTC (référence crypto).",
        "logic": "Asset et BTC montent ensemble → BUY (tendance confirmée). Les deux baissent → SELL.",
        "formula": "BUY si asset_ret > 0 ET btc_ret > 0 | SELL si les deux < 0",
        "chart_type": "correlation",
        "emoji": "🔗",
    },
    "SignalAggregatorAgent": {
        "role": "Agent méta : agrège les votes de tous les autres agents. Ne vote pas directement.",
        "logic": "Calcule la somme pondérée des votes BUY/SELL/HOLD. La direction avec le plus grand poids gagne.",
        "formula": "side = argmax(buy_weight, sell_weight, hold_weight) | confidence = top_weight / total",
        "chart_type": "aggregation",
        "emoji": "🧮",
    },
    "PredictionAgent": {
        "role": "Calcule un score de risque composite (volatilité + événement + spread).",
        "logic": "Score composite > 0.70 → SELL (trop risqué). Score < 0.35 → BUY (conditions favorables).",
        "formula": "composite = min(1, rv20×10 + event×0.7 + spread/100) | SELL si > 0.70",
        "chart_type": "composite_risk",
        "emoji": "🔮",
    },
    "PortfolioAgent": {
        "role": "Surveille l'exposition et le drawdown du portefeuille pour éviter la sur-exposition.",
        "logic": "Drawdown > 10% ou exposition > 80% → SELL (protection). Exposition < 30% et drawdown faible → BUY.",
        "formula": "SELL si drawdown > 0.10 ou exposure > 0.80 | BUY si exposure < 0.30",
        "chart_type": "portfolio",
        "emoji": "🏦",
    },
}


def _signal_color(signal: str) -> str:
    return {"BUY": "#69db7c", "SELL": "#f783ac", "HOLD": "#adb5bd"}.get(signal, "#adb5bd")


def _build_price_chart(state: MarketState, title: str = "Prix") -> go.Figure:
    prices = list(state.prices)[-50:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=prices, mode="lines", name="Prix",
        line=dict(color="#74c0fc", width=2)
    ))
    fig.update_layout(
        title=title, height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
    )
    return fig


def _build_rsi_chart(state: MarketState) -> go.Figure:
    prices = list(state.prices)
    rsi_vals = []
    for i in range(14, len(prices) + 1):
        r = rsi(prices[:i], 14)
        rsi_vals.append(r if r is not None else 50.0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=rsi_vals, mode="lines", name="RSI(14)",
                             line=dict(color="#ffd43b", width=2)))
    fig.add_hline(y=70, line_dash="dash", line_color="#f783ac", annotation_text="Suracheté (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#69db7c", annotation_text="Survendu (30)")
    fig.update_layout(
        title="RSI (14 périodes)", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
        xaxis=dict(showgrid=False),
    )
    return fig


def _build_bollinger_chart(state: MarketState) -> go.Figure:
    prices = list(state.prices)[-50:]
    lower_vals, mid_vals, upper_vals = [], [], []
    for i in range(20, len(prices) + 1):
        l, m, u = bollinger(prices[:i], 20, 2.0)
        lower_vals.append(l or prices[i - 1])
        mid_vals.append(m or prices[i - 1])
        upper_vals.append(u or prices[i - 1])

    x = list(range(len(lower_vals)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=upper_vals, mode="lines", name="BB Upper",
                             line=dict(color="#f783ac", width=1, dash="dash")))
    fig.add_trace(go.Scatter(x=x, y=mid_vals, mode="lines", name="SMA20",
                             line=dict(color="#adb5bd", width=1)))
    fig.add_trace(go.Scatter(x=x, y=lower_vals, mode="lines", name="BB Lower",
                             line=dict(color="#69db7c", width=1, dash="dash"),
                             fill="tonexty", fillcolor="rgba(105,219,124,0.05)"))
    fig.add_trace(go.Scatter(x=x, y=prices[20:], mode="lines", name="Prix",
                             line=dict(color="#74c0fc", width=2)))
    fig.update_layout(
        title="Bollinger Bands (20, ±2σ)", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
    )
    return fig


def _build_macd_chart(state: MarketState) -> go.Figure:
    prices = list(state.prices)
    macd_vals, signal_vals, hist_vals = [], [], []
    for i in range(35, len(prices) + 1):
        m, s, h = macd(prices[:i])
        macd_vals.append(m or 0.0)
        signal_vals.append(s or 0.0)
        hist_vals.append(h or 0.0)

    colors = ["#69db7c" if h >= 0 else "#f783ac" for h in hist_vals]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=hist_vals, name="Histogramme",
                         marker_color=colors, opacity=0.7))
    fig.add_trace(go.Scatter(y=macd_vals, mode="lines", name="MACD",
                             line=dict(color="#74c0fc", width=2)))
    fig.add_trace(go.Scatter(y=signal_vals, mode="lines", name="Signal",
                             line=dict(color="#ffd43b", width=1, dash="dash")))
    fig.update_layout(
        title="MACD (12,26,9)", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
    )
    return fig


def _build_volume_chart(state: MarketState) -> go.Figure:
    vols = list(state.volumes)[-50:]
    avg = sum(vols[-20:]) / 20 if len(vols) >= 20 else sum(vols) / max(len(vols), 1)
    colors = ["#69db7c" if v > avg else "#f783ac" for v in vols]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=vols, name="Volume", marker_color=colors, opacity=0.8))
    fig.add_hline(y=avg, line_dash="dash", line_color="#ffd43b",
                  annotation_text=f"Moy. 20 = {avg:,.0f}")
    fig.update_layout(
        title="Volume (50 dernières périodes)", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
    )
    return fig


def _build_event_risk_chart(state: MarketState) -> go.Figure:
    risks = list(state.event_risk_scores)[-50:]
    colors = ["#f783ac" if r > 0.65 else "#ffd43b" if r > 0.30 else "#69db7c" for r in risks]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=risks, name="Event Risk", marker_color=colors, opacity=0.8))
    fig.add_hline(y=0.65, line_dash="dash", line_color="#f783ac", annotation_text="Seuil SELL (0.65)")
    fig.add_hline(y=0.30, line_dash="dash", line_color="#69db7c", annotation_text="Seuil BUY (0.30)")
    fig.update_layout(
        title="Score de Risque Événementiel", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        yaxis=dict(range=[0, 1], showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
        xaxis=dict(showgrid=False),
    )
    return fig


def _build_breakout_chart(state: MarketState) -> go.Figure:
    prices = list(state.prices)[-50:]
    highs = list(state.highs)[-50:]
    lows = list(state.lows)[-50:]
    resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs) if highs else 0
    support = min(lows[-20:]) if len(lows) >= 20 else min(lows) if lows else 0
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=prices, mode="lines", name="Prix",
                             line=dict(color="#74c0fc", width=2)))
    fig.add_hline(y=resistance, line_dash="dash", line_color="#f783ac",
                  annotation_text=f"Résistance {resistance:,.0f}")
    fig.add_hline(y=support, line_dash="dash", line_color="#69db7c",
                  annotation_text=f"Support {support:,.0f}")
    fig.update_layout(
        title="Support & Résistance (20 périodes)", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
    )
    return fig


def _build_aggregation_chart(votes: list[AgentVote]) -> go.Figure:
    active = [v for v in votes if v.name != "SignalAggregatorAgent"]
    buy_w = sum(v.confidence for v in active if v.signal == "BUY")
    sell_w = sum(v.confidence for v in active if v.signal == "SELL")
    hold_w = sum(v.confidence for v in active if v.signal == "HOLD")
    fig = go.Figure(go.Bar(
        x=["BUY", "SELL", "HOLD"],
        y=[buy_w, sell_w, hold_w],
        marker_color=["#69db7c", "#f783ac", "#adb5bd"],
        text=[f"{v:.3f}" for v in [buy_w, sell_w, hold_w]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Poids de vote agrégé (somme des confiances)", height=220,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,30,0.8)",
        font=dict(color="#adb5bd", size=11),
        yaxis=dict(showgrid=True, gridcolor="rgba(100,100,120,0.2)"),
    )
    return fig


def render_agent_deep_dive(state: MarketState, votes: list[AgentVote]) -> None:
    """Rendu de la section Agent Deep Dive dans Streamlit."""
    st.subheader("🧠 Agent Deep Dive — Raisonnement Transparent")
    st.caption("Sélectionnez un agent pour voir exactement ses données, sa logique et son graphique.")

    agent_names = [v.name for v in votes]
    selected_name = st.selectbox(
        "Choisir un agent à analyser :",
        agent_names,
        format_func=lambda n: f"{AGENT_DESCRIPTIONS.get(n, {}).get('emoji', '🤖')} {n}",
        key="deep_dive_select",
    )

    selected_vote = next((v for v in votes if v.name == selected_name), None)
    if not selected_vote:
        return

    desc = AGENT_DESCRIPTIONS.get(selected_name, {})
    signal_col = _signal_color(selected_vote.signal)

    # ── En-tête de l'agent ──────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        st.markdown(f"### {desc.get('emoji', '🤖')} {selected_name}")
        st.markdown(f"**Famille :** `{selected_vote.category}`")
        st.markdown(f"*{desc.get('role', '')}*")
    with col_b:
        st.markdown(f"**Signal actuel**")
        st.markdown(
            f"<div style='background:{signal_col}22;border:1px solid {signal_col};"
            f"border-radius:8px;padding:12px;text-align:center;"
            f"font-size:1.4em;font-weight:bold;color:{signal_col}'>"
            f"{selected_vote.signal}</div>",
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown(f"**Confiance**")
        conf_pct = int(selected_vote.confidence * 100)
        st.markdown(
            f"<div style='background:#1a1a2e;border:1px solid #444;"
            f"border-radius:8px;padding:12px;text-align:center;"
            f"font-size:1.4em;font-weight:bold;color:#ffd43b'>"
            f"{conf_pct}%</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Raisonnement ────────────────────────────────────────────────────────
    col_logic, col_data = st.columns(2)
    with col_logic:
        st.markdown("**🧩 Logique de décision**")
        st.info(desc.get("logic", ""))
        st.code(desc.get("formula", ""), language="python")

    with col_data:
        st.markdown("**📊 Données brutes ingérées**")
        price = state.prices[-1] if state.prices else 0.0
        data_rows = {
            "Prix actuel": f"${price:,.2f}",
            "Rationale": selected_vote.rationale,
        }
        if len(state.prices) >= 2:
            data_rows["Prix t-1"] = f"${state.prices[-2]:,.2f}"
        if len(state.prices) >= 6:
            data_rows["Prix t-5"] = f"${state.prices[-6]:,.2f}"
        if state.volumes:
            data_rows["Volume actuel"] = f"{state.volumes[-1]:,.0f}"
        if state.event_risk_scores:
            data_rows["Event Risk"] = f"{state.event_risk_scores[-1]:.3f}"
        if state.sentiment_scores:
            data_rows["Sentiment"] = f"{state.sentiment_scores[-1]:.3f}"

        for k, v in data_rows.items():
            st.markdown(f"- **{k}** : `{v}`")

    st.divider()

    # ── Graphique spécifique ────────────────────────────────────────────────
    st.markdown("**📈 Visualisation de l'indicateur**")
    chart_type = desc.get("chart_type", "price_change")

    try:
        if chart_type == "rsi":
            if len(state.prices) >= 15:
                st.plotly_chart(_build_rsi_chart(state), width="stretch")
            else:
                st.info("Accumulation de données en cours (besoin de 15 prix)...")
        elif chart_type == "bollinger":
            if len(state.prices) >= 21:
                st.plotly_chart(_build_bollinger_chart(state), width="stretch")
            else:
                st.info("Accumulation de données en cours (besoin de 21 prix)...")
        elif chart_type == "macd":
            if len(state.prices) >= 36:
                st.plotly_chart(_build_macd_chart(state), width="stretch")
            else:
                st.info("Accumulation de données en cours (besoin de 36 prix)...")
        elif chart_type == "volume":
            if len(state.volumes) >= 2:
                st.plotly_chart(_build_volume_chart(state), width="stretch")
            else:
                st.info("Accumulation de données de volume...")
        elif chart_type in ("event_risk", "composite_risk"):
            if len(state.event_risk_scores) >= 2:
                st.plotly_chart(_build_event_risk_chart(state), width="stretch")
            else:
                st.info("Accumulation de données de risque...")
        elif chart_type == "breakout":
            if len(state.prices) >= 21:
                st.plotly_chart(_build_breakout_chart(state), width="stretch")
            else:
                st.info("Accumulation de données en cours (besoin de 21 prix)...")
        elif chart_type == "aggregation":
            st.plotly_chart(_build_aggregation_chart(votes), width="stretch")
        elif chart_type == "portfolio":
            st.info("Graphique portfolio : voir la section NAV & Drawdown dans l'historique.")
        else:
            if len(state.prices) >= 2:
                st.plotly_chart(_build_price_chart(state, "Évolution du Prix"), width="stretch")
            else:
                st.info("Accumulation de données de prix...")
    except Exception as e:
        st.warning(f"Graphique indisponible : {e}")
