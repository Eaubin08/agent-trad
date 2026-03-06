"""
Page 2 — Agents
Constellation des 14 agents avec votes, consensus et Deep Dive par agent.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

from agents.registry import build_default_agents, aggregate_votes, AgentVote
from agents.indicators import (
    MarketState, rsi, macd, atr, sma, realized_volatility, structural_score
)
from core.live_market import MockMarketFeed, LiveMarketFeed

st.set_page_config(page_title="Agents — Obsidia", page_icon="🧠", layout="wide")

st.title("🧠 Constellation des 14 Agents")
st.caption("Chaque agent analyse le marché de façon indépendante. Le consensus détermine la direction.")

# ─── Initialisation ──────────────────────────────────────────────────────────
if "agents" not in st.session_state:
    st.session_state.agents = build_default_agents()

sim_mode = st.session_state.get("sim_mode", True)
drift_bias = st.session_state.get("drift_bias", 0.0)
vol_mult = st.session_state.get("vol_mult", 1.0)

# ─── Récupération du marché ───────────────────────────────────────────────────
@st.cache_data(ttl=2)
def get_market(sim: bool, drift: float, vol: float):
    if sim:
        feed = MockMarketFeed(drift_bias=drift, volatility_multiplier=vol)
    else:
        feed = LiveMarketFeed()
    m = feed.get_state()
    return m if m else MockMarketFeed().get_state()

if st.button("🔄 Rafraîchir les votes", type="primary"):
    st.cache_data.clear()

market = get_market(sim_mode, drift_bias, vol_mult)
votes = [a.vote(market) for a in st.session_state.agents]
agg = aggregate_votes(votes)

# ─── Résumé du consensus ─────────────────────────────────────────────────────
st.subheader("🎯 Consensus pondéré")
col1, col2, col3, col4 = st.columns(4)
with col1:
    direction_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(agg.direction, "⚪")
    st.metric("Direction", f"{direction_icon} {agg.direction}")
with col2:
    st.metric("Confiance", f"{agg.confidence:.1%}")
with col3:
    buy_count = sum(1 for v in votes if v.signal == "BUY")
    sell_count = sum(1 for v in votes if v.signal == "SELL")
    hold_count = sum(1 for v in votes if v.signal == "HOLD")
    st.metric("Votes BUY / HOLD / SELL", f"{buy_count} / {hold_count} / {sell_count}")
with col4:
    st.metric("Agents actifs", len(votes))

# Barre de consensus visuelle
st.progress(float(agg.confidence), text=f"Confiance globale : {agg.confidence:.1%}")

st.divider()

# ─── Tableau des 14 agents ────────────────────────────────────────────────────
st.subheader("📋 Votes détaillés")

FAMILIES = {
    "Observation": ["PriceAgent", "VolumeAgent", "SpreadAgent"],
    "Technique": ["RSIAgent", "MACDAgent", "BollingerAgent", "ATRAgent", "MomentumAgent"],
    "Contexte": ["VolatilityAgent", "TrendAgent", "RegimeAgent"],
    "Stratégie": ["MeanReversionAgent", "PortfolioAgent", "RiskAgent"],
}

vote_map = {v.agent_name: v for v in votes}

for family, agent_names in FAMILIES.items():
    family_icon = {"Observation": "👁️", "Technique": "📐", "Contexte": "🌍", "Stratégie": "♟️"}.get(family, "🔹")
    st.markdown(f"**{family_icon} Famille {family}**")

    rows = []
    for name in agent_names:
        v = vote_map.get(name)
        if v:
            signal_icon = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "HOLD": "🟡 HOLD"}.get(v.signal, "⚪")
            rows.append({
                "Agent": name,
                "Signal": signal_icon,
                "Confiance": f"{v.confidence:.1%}",
                "Poids": f"{v.weight:.2f}",
                "Rationale": v.rationale[:80] + "..." if len(v.rationale) > 80 else v.rationale,
            })

    if rows:
        df_fam = pd.DataFrame(rows)
        st.dataframe(df_fam, use_container_width=True, hide_index=True)

st.divider()

# ─── Deep Dive par agent ──────────────────────────────────────────────────────
st.subheader("🔬 Agent Deep Dive — Raisonnement Transparent")
st.caption("Sélectionnez un agent pour voir exactement ses données, sa logique et son graphique.")

agent_names_all = [v.agent_name for v in votes]
selected = st.selectbox("Choisir un agent", agent_names_all, index=0)

v_sel = vote_map.get(selected)
if v_sel:
    col_info, col_graph = st.columns([1, 2])

    with col_info:
        signal_color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(v_sel.signal, "⚪")
        st.markdown(f"### {signal_color} {v_sel.signal}")
        st.metric("Confiance", f"{v_sel.confidence:.1%}")
        st.metric("Poids dans le consensus", f"{v_sel.weight:.2f}")

        st.markdown("**Raisonnement :**")
        st.info(v_sel.rationale)

        st.markdown("**Données utilisées :**")

        # Données spécifiques selon l'agent
        if selected == "RSIAgent":
            rsi_val = market.rsi
            status = "Suracheté (signal SELL)" if rsi_val > 70 else ("Survendu (signal BUY)" if rsi_val < 30 else "Zone neutre (HOLD)")
            st.markdown(f"- RSI(14) = **{rsi_val:.1f}**")
            st.markdown(f"- Statut : {status}")
            st.markdown("- Formule : `RSI = 100 - 100/(1 + RS)`")

        elif selected == "MACDAgent":
            st.markdown(f"- Prix actuel : **${market.price:,.2f}**")
            st.markdown(f"- Volatilité : **{market.volatility:.4f}**")
            st.markdown("- Formule : `MACD = EMA(12) - EMA(26)`")
            st.markdown("- Signal : `EMA(9) du MACD`")

        elif selected == "BollingerAgent":
            st.markdown(f"- Prix : **${market.price:,.2f}**")
            st.markdown(f"- Volatilité σ : **{market.volatility:.4f}**")
            st.markdown("- Formule : `BB = SMA(20) ± 2σ`")

        elif selected == "ATRAgent":
            st.markdown(f"- ATR(14) : **{market.atr:.4f}**")
            st.markdown(f"- Spread : **{market.spread:.4f}**")
            st.markdown("- Formule : `ATR = EMA(TR, 14)`")

        elif selected in ("PriceAgent", "MomentumAgent"):
            st.markdown(f"- Prix : **${market.price:,.2f}**")
            st.markdown(f"- RSI : **{market.rsi:.1f}**")
            st.markdown("- Formule : `Momentum = P(t) / P(t-n) - 1`")

        elif selected == "VolumeAgent":
            st.markdown(f"- Volume : **{market.volume:,.0f}**")
            st.markdown("- Seuil : Volume > moyenne × 1.5 → signal fort")

        elif selected == "VolatilityAgent":
            st.markdown(f"- Volatilité réalisée : **{market.volatility:.4f}**")
            st.markdown("- Seuil haut : 0.03 → HOLD (trop risqué)")
            st.markdown("- Seuil bas : 0.005 → BUY (marché calme)")

        elif selected == "TrendAgent":
            st.markdown(f"- RSI : **{market.rsi:.1f}**")
            st.markdown(f"- Volatilité : **{market.volatility:.4f}**")
            st.markdown("- Tendance haussière si RSI > 55 et vol < 0.025")

        elif selected in ("PortfolioAgent", "RiskAgent"):
            nav = st.session_state.get("portfolio")
            if nav:
                nav_dict = nav.as_dict()
                st.markdown(f"- NAV : **${nav_dict['nav']:,.2f}**")
                st.markdown(f"- PnL : **${nav_dict['total_pnl']:+,.2f}**")
                st.markdown(f"- Drawdown : **{nav_dict['max_drawdown']:.2%}**")
            st.markdown("- Limite de risque : drawdown max 15%")

        else:
            st.markdown(f"- Prix : **${market.price:,.2f}**")
            st.markdown(f"- RSI : **{market.rsi:.1f}**")
            st.markdown(f"- Volatilité : **{market.volatility:.4f}**")

    with col_graph:
        st.markdown("**Visualisation de l'indicateur**")

        # Générer un historique simulé pour l'indicateur
        import random
        import math

        n_points = 60
        prices = [market.price * (1 + random.gauss(0, market.volatility)) for _ in range(n_points)]
        prices[-1] = market.price

        if selected == "RSIAgent":
            # Simuler RSI sur 60 points
            rsi_vals = []
            for i in range(n_points):
                base = 50 + 20 * math.sin(i / 10) + random.gauss(0, 5)
                rsi_vals.append(max(0, min(100, base)))
            rsi_vals[-1] = market.rsi
            df_rsi = pd.DataFrame({"RSI": rsi_vals, "Suracheté (70)": [70]*n_points, "Survendu (30)": [30]*n_points})
            st.line_chart(df_rsi, height=300)

        elif selected in ("MACDAgent",):
            macd_line = [random.gauss(0, 0.5) for _ in range(n_points)]
            signal_line = [sum(macd_line[max(0,i-9):i+1])/(min(i+1,9)) for i in range(n_points)]
            df_macd = pd.DataFrame({"MACD": macd_line, "Signal": signal_line})
            st.line_chart(df_macd, height=300)

        elif selected == "BollingerAgent":
            sma_vals = [sum(prices[max(0,i-20):i+1])/min(i+1,20) for i in range(n_points)]
            std_vals = [max(0.5, abs(prices[i] - sma_vals[i]) * 2) for i in range(n_points)]
            df_bb = pd.DataFrame({
                "Prix": prices,
                "BB Sup": [sma_vals[i] + std_vals[i] for i in range(n_points)],
                "SMA(20)": sma_vals,
                "BB Inf": [sma_vals[i] - std_vals[i] for i in range(n_points)],
            })
            st.line_chart(df_bb, height=300)

        elif selected == "ATRAgent":
            atr_vals = [abs(random.gauss(market.atr, market.atr * 0.3)) for _ in range(n_points)]
            atr_vals[-1] = market.atr
            df_atr = pd.DataFrame({"ATR(14)": atr_vals})
            st.line_chart(df_atr, height=300, color="#f0883e")

        elif selected == "VolatilityAgent":
            vol_vals = [abs(random.gauss(market.volatility, market.volatility * 0.3)) for _ in range(n_points)]
            vol_vals[-1] = market.volatility
            df_vol = pd.DataFrame({
                "Volatilité": vol_vals,
                "Seuil haut (0.03)": [0.03]*n_points,
                "Seuil bas (0.005)": [0.005]*n_points,
            })
            st.line_chart(df_vol, height=300)

        else:
            # Graphique prix par défaut
            df_price = pd.DataFrame({"Prix": prices})
            st.line_chart(df_price, height=300, color="#58a6ff")

        # Score structurel Obsidia
        st.markdown("**Score structurel Obsidia (OS2)**")
        score = structural_score(market)
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("T (Trend)", f"{score.get('T', 0):.3f}")
        with col_s2:
            st.metric("H (Harmony)", f"{score.get('H', 0):.3f}")
        with col_s3:
            st.metric("A (Anomaly)", f"{score.get('A', 0):.3f}")
        with col_s4:
            st.metric("S (Score final)", f"{score.get('S', 0):.3f}")
        st.caption("Formule : S = α·T + β·H − γ·A (moteur Obsidia v18.3)")
