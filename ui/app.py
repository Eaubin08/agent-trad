"""
Obsidia x ERC-8004 — Dashboard Streamlit
Démo hackathon : 14 agents déterministes + Guard X-108 + ERC-8004 + Decision Flow
"""
from __future__ import annotations

import os
import sys
import time

import pandas as pd
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.registry import build_default_agents, aggregate_votes
from blockchain.eip712_signer import EIP712Signer
from blockchain.erc8004_client import ERC8004Client
from config.settings import (
    AGENT_PROFILE, TRADING_SYMBOL, POSITION_SIZE_PCT, INITIAL_CAPITAL,
    GUARD_BASE_THRESHOLD, GUARD_MIN_CONSENSUS, GUARD_THETA_S, GUARD_MIN_WAIT_S,
)
from core.guard_x108 import GuardX108
from core.live_market import LiveMarketFeed, MockMarketFeed
from core.logger import ProofLogger
from core.portfolio import Portfolio
from ui.components.agent_deep_dive import render_agent_deep_dive

# ── Configuration de la page ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Obsidia x ERC-8004",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialisation de la session ─────────────────────────────────────────────
if "feed" not in st.session_state:
    st.session_state.feed = LiveMarketFeed(symbol=TRADING_SYMBOL)
if "agents" not in st.session_state:
    st.session_state.agents = build_default_agents()
if "guard" not in st.session_state:
    st.session_state.guard = GuardX108(
        base_threshold=GUARD_BASE_THRESHOLD,
        min_consensus=GUARD_MIN_CONSENSUS,
        theta_S=GUARD_THETA_S,
        min_wait_s=GUARD_MIN_WAIT_S,
    )
if "portfolio" not in st.session_state:
    st.session_state.portfolio = Portfolio(initial_cash=INITIAL_CAPITAL)
if "logger" not in st.session_state:
    st.session_state.logger = ProofLogger(path=os.path.join(ROOT, "logs"))
if "erc" not in st.session_state:
    st.session_state.erc = ERC8004Client()
if "signer" not in st.session_state:
    st.session_state.signer = EIP712Signer()
if "identity" not in st.session_state:
    st.session_state.identity = st.session_state.erc.register_identity(AGENT_PROFILE)
if "history" not in st.session_state:
    st.session_state.history = []
if "cycle_count" not in st.session_state:
    st.session_state.cycle_count = 0
if "trade_count" not in st.session_state:
    st.session_state.trade_count = 0
if "mock_feed" not in st.session_state:
    st.session_state.mock_feed = MockMarketFeed(symbol=TRADING_SYMBOL)
if "force_mock" not in st.session_state:
    st.session_state.force_mock = False
if "drift_bias" not in st.session_state:
    st.session_state.drift_bias = 0.0
if "vol_mult" not in st.session_state:
    st.session_state.vol_mult = 1.0
if "guard_theta" not in st.session_state:
    st.session_state.guard_theta = GUARD_THETA_S

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/ERC--8004-Hackathon-blueviolet?style=for-the-badge", use_container_width=True)
    st.subheader("🔮 Obsidia Trustless Agent")
    st.caption("14 agents • Guard X-108 • ERC-8004")
    st.divider()

    st.subheader("Hackathon Flow")
    st.markdown("""
    1. ✅ **Identity Registry** — Agent enregistré
    2. 📊 **14 Agents** — Votes déterministes
    3. 🧠 **Guard X-108** — Validation structurelle
    4. 🔐 **Validation Registry** — Preuve pré-trade
    5. 🚦 **Risk Router** — Exécution trustless
    6. 📋 **Proof Logs** — Audit trail
    """)
    st.divider()

    st.subheader("Agent Identity")
    st.json(st.session_state.identity)
    st.divider()

    feed_status = "🟢 LIVE (Binance)" if (not st.session_state.force_mock and st.session_state.feed.is_live) else "🟡 MOCK (Simulation)"
    st.metric("Market Feed", feed_status)
    st.metric("Cycles", st.session_state.cycle_count)
    st.metric("Trades", st.session_state.trade_count)
    st.divider()

    # ── Panneau Market & Risk Control ────────────────────────────────────────
    st.subheader("🎛️ Market & Risk Control")
    st.caption("Contrôlez le marché simulé et les seuils du Guard X-108")

    force_mock = st.toggle(
        "🔬 Forcer le mode Simulation",
        value=st.session_state.force_mock,
        help="Désactive Binance et utilise un marché simulé contrôlable",
    )
    if force_mock != st.session_state.force_mock:
        st.session_state.force_mock = force_mock

    if st.session_state.force_mock:
        st.markdown("**📈 Tendance du marché simulé**")
        drift = st.slider(
            "Biais directionnel",
            min_value=-0.030, max_value=0.030, value=st.session_state.drift_bias,
            step=0.001, format="%.3f",
            help="Négatif = baissier, Positif = haussier",
        )
        if drift != st.session_state.drift_bias:
            st.session_state.drift_bias = drift
            st.session_state.mock_feed.drift_bias = drift

        vol_mult = st.slider(
            "Multiplicateur de volatilité",
            min_value=0.1, max_value=5.0, value=st.session_state.vol_mult,
            step=0.1, format="%.1fx",
            help="1.0 = normal, 3.0 = marché très agité",
        )
        if vol_mult != st.session_state.vol_mult:
            st.session_state.vol_mult = vol_mult
            st.session_state.mock_feed.volatility_multiplier = vol_mult

        if st.button("⚡ Injecter Flash Crash", use_container_width=True, type="primary"):
            st.session_state.mock_feed.flash_crash = True
            st.warning("Flash crash injecté ! Il sera appliqué au prochain cycle.")

    st.divider()
    st.markdown("**🛡️ Guard X-108 — Seuil de sécurité**")
    guard_theta = st.slider(
        "Seuil de cohésion θ_S",
        min_value=0.05, max_value=0.60, value=st.session_state.guard_theta,
        step=0.01, format="%.2f",
        help="Plus élevé = Guard plus strict (bloque plus de trades)",
    )
    if guard_theta != st.session_state.guard_theta:
        st.session_state.guard_theta = guard_theta
        st.session_state.guard = GuardX108(
            base_threshold=GUARD_BASE_THRESHOLD,
            min_consensus=GUARD_MIN_CONSENSUS,
            theta_S=guard_theta,
            min_wait_s=GUARD_MIN_WAIT_S,
        )
    st.caption(f"Seuil actuel : **{guard_theta:.2f}** (défaut : {GUARD_THETA_S})")

# ── Titre ────────────────────────────────────────────────────────────────────
st.title("🔮 Obsidia — Trustless Multi-Agent Trading System")
st.caption(
    "**Every trade is governed, explainable, and provable before execution.** "
    "| AI Trading Agents ERC-8004 Hackathon"
)

# ── Exécution du cycle ───────────────────────────────────────────────────────
# Choix du feed : live Binance ou mock contrôlable
if st.session_state.force_mock:
    state = st.session_state.mock_feed.next()
else:
    state = st.session_state.feed.next()
portfolio = st.session_state.portfolio

# Mise à jour des agents Portfolio avec l'état courant
agents = build_default_agents(
    exposure=portfolio.exposure(),
    drawdown=portfolio.state.drawdown,
)

# Votes des 14 agents
votes = [a.vote(state) for a in agents]
consensus = aggregate_votes(votes)

# Données de marché
price = state.prices[-1] if state.prices else 0.0
volatility = state.event_risk_scores[-1] if state.event_risk_scores else 0.0
event_risk = state.event_risk_scores[-1] if state.event_risk_scores else 0.0
prediction_risk = min(1.0, (volatility + event_risk) / 2)

# Guard X-108
guard_result = st.session_state.guard.evaluate(
    votes=votes,
    consensus=consensus,
    snapshot_volatility=volatility,
    snapshot_event_risk=event_risk,
    exposure=portfolio.exposure(),
    drawdown=portfolio.state.drawdown,
    prediction_risk=prediction_risk,
)

# Calcul de la quantité
nav = portfolio.state.nav or INITIAL_CAPITAL
quantity = round((nav * POSITION_SIZE_PCT) / price, 6) if price > 0 and consensus["side"] != "HOLD" else 0.0

# Signature EIP-712
signed = st.session_state.signer.sign_trade_intent(
    symbol=TRADING_SYMBOL,
    side=consensus["side"],
    quantity=quantity,
    price=price,
    confidence=consensus["confidence"],
    artifact_hash=guard_result.validation_artifact.get("artifact_hash", ""),
    agent_id=st.session_state.identity.get("agent_id", "obsidia"),
)

# Validation Registry (pré-trade)
validation = st.session_state.erc.submit_validation(guard_result.validation_artifact)

# Risk Router (exécution)
router = st.session_state.erc.route_trade_intent(signed)

# Application au portfolio
portfolio_state = portfolio.apply(
    side=consensus["side"],
    price=price,
    quantity=quantity,
    decision=guard_result.decision.value,
)

# Proof Log
proof = st.session_state.logger.write({
    "cycle": st.session_state.cycle_count,
    "symbol": TRADING_SYMBOL,
    "price": price,
    "votes_summary": {
        "buy": sum(1 for v in votes if v.signal == "BUY"),
        "sell": sum(1 for v in votes if v.signal == "SELL"),
        "hold": sum(1 for v in votes if v.signal == "HOLD"),
    },
    "consensus": consensus,
    "guard": {
        "decision": guard_result.decision.value,
        "reason": guard_result.reason,
        "structural_S": guard_result.structural_S,
        "risk_score": guard_result.risk_score,
    },
    "trade": {"side": consensus["side"], "quantity": quantity, "price": price},
    "validation": validation,
    "router": router,
    "portfolio": portfolio_state.as_dict(),
})

# Mise à jour des compteurs
st.session_state.cycle_count += 1
if guard_result.decision.value == "ALLOW" and consensus["side"] != "HOLD":
    st.session_state.trade_count += 1

# Historique
st.session_state.history.append({
    "cycle": st.session_state.cycle_count,
    "price": price,
    "decision": guard_result.decision.value,
    "side": consensus["side"],
    "confidence": consensus["confidence"],
    "structural_S": guard_result.structural_S,
    "nav": portfolio_state.nav,
    "pnl": portfolio_state.realized_pnl,
})

# ── Métriques principales ────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(
    "💰 Prix",
    f"${price:,.2f}",
    f"{((price - state.prices[-2]) / state.prices[-2] * 100):.2f}%" if len(state.prices) >= 2 else "—",
)
col2.metric(
    "🧠 Guard X-108",
    guard_result.decision.value,
    guard_result.reason[:30] + "..." if len(guard_result.reason) > 30 else guard_result.reason,
)
col3.metric(
    "📐 Score Structurel S",
    f"{guard_result.structural_S:.3f}",
    f"seuil={GUARD_THETA_S}",
)
col4.metric(
    "📊 NAV Portfolio",
    f"${portfolio_state.nav:,.2f}",
    f"PnL {portfolio_state.realized_pnl:+.2f}$",
)
col5.metric(
    "⚠️ Risk Score",
    f"{guard_result.risk_score:.2f}",
    f"Expo {portfolio.exposure():.0%}",
)

st.divider()

# ── Decision Flow ────────────────────────────────────────────────────────────
st.subheader("🔄 Decision Flow")
flow_cols = st.columns(7)

DECISION_COLOR = {
    "ALLOW": "🟢",
    "HOLD": "🟡",
    "BLOCK": "🔴",
}

flow_cols[0].info(f"**Market**\n\n{TRADING_SYMBOL}\n${price:,.0f}")
flow_cols[1].info(f"**14 Agents**\n\nBUY:{sum(1 for v in votes if v.signal=='BUY')} SELL:{sum(1 for v in votes if v.signal=='SELL')} HOLD:{sum(1 for v in votes if v.signal=='HOLD')}")
flow_cols[2].info(f"**Consensus**\n\n{consensus['side']}\nconf={consensus['confidence']:.2f}")
flow_cols[3].info(f"**Prediction**\n\nRisk={prediction_risk:.2f}\nVol={volatility:.2f}")
flow_cols[4].info(f"**Guard X-108**\n\n{DECISION_COLOR.get(guard_result.decision.value, '')} {guard_result.decision.value}\nS={guard_result.structural_S:.3f}")
flow_cols[5].info(f"**ERC-8004**\n\nValidation ✓\nRouter ✓")
flow_cols[6].info(f"**Proof**\n\n{proof['hash'][:10]}...\n✅ Logged")

st.divider()

# ── Constellation des 14 agents ──────────────────────────────────────────────
left, right = st.columns([1.3, 1])

with left:
    st.subheader("🌌 Constellation des 14 Agents")
    sig_df = pd.DataFrame([
        {
            "Agent": v.name,
            "Famille": v.category,
            "Signal": v.signal,
            "Confiance": round(v.confidence, 3),
            "Rationale": v.rationale,
        }
        for v in votes
    ])

    def color_signal(val):
        if val == "BUY":
            return "background-color: #1a472a; color: #69db7c"
        elif val == "SELL":
            return "background-color: #4a1942; color: #f783ac"
        return "background-color: #2b2d42; color: #adb5bd"

    # applymap est déprécié depuis pandas 2.1 → utiliser map
    try:
        styled = sig_df.style.map(color_signal, subset=["Signal"])
    except AttributeError:
        styled = sig_df.style.applymap(color_signal, subset=["Signal"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.subheader("📊 Consensus pondéré")
    agg_df = pd.DataFrame([
        {"Direction": "BUY", "Score": round(consensus["buy_weight"], 3)},
        {"Direction": "SELL", "Score": round(consensus["sell_weight"], 3)},
        {"Direction": "HOLD", "Score": round(consensus["hold_weight"], 3)},
    ])
    if agg_df["Score"].sum() > 0:
        st.bar_chart(agg_df.set_index("Direction"))
    else:
        st.info("En attente de données de consensus...")

with right:
    st.subheader("🔐 Guard X-108 — Détail")
    guard_color = {"ALLOW": "success", "HOLD": "warning", "BLOCK": "error"}
    getattr(st, guard_color.get(guard_result.decision.value, "info"))(
        f"**{guard_result.decision.value}** — {guard_result.reason}"
    )
    st.json({
        "decision": guard_result.decision.value,
        "reason": guard_result.reason,
        "structural_S": round(guard_result.structural_S, 4),
        "theta_S": GUARD_THETA_S,
        "risk_score": round(guard_result.risk_score, 4),
        "x108_elapsed_s": guard_result.validation_artifact.get("x108_elapsed_s"),
        "x108_min_wait_s": GUARD_MIN_WAIT_S,
    })

    st.subheader("⛓️ ERC-8004 Hooks")
    st.json({
        "identity": {
            "agent_id": st.session_state.identity.get("agent_id"),
            "chain": st.session_state.identity.get("chain"),
            "mode": st.session_state.identity.get("mode"),
        },
        "validation": {
            "status": validation.get("status"),
            "artifact_hash": guard_result.validation_artifact.get("artifact_hash", "")[:16] + "...",
        },
        "risk_router": {
            "status": router.get("status"),
            "mode": router.get("mode"),
        },
        "signature": signed.get("signature", "")[:20] + "...",
    })

    st.subheader("📋 Proof Log")
    st.json({
        "hash": proof["hash"][:16] + "...",
        "recorded_at": proof["recorded_at"],
        "file": os.path.basename(proof.get("file", "")),
    })

st.divider()

# ── Agent Deep Dive ──────────────────────────────────────────────────────────
st.divider()
render_agent_deep_dive(state, votes)

st.divider()

# ── Historique ───────────────────────────────────────────────────────────────
st.subheader("📈 Historique des cycles")
if st.session_state.history:
    hist_df = pd.DataFrame(st.session_state.history[-50:])
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if "price" in hist_df.columns and len(hist_df) >= 2:
            st.line_chart(hist_df.set_index("cycle")[["price"]], height=200)
        else:
            st.info("Accumulation des données de prix...")
    with col_chart2:
        if "nav" in hist_df.columns and len(hist_df) >= 2:
            st.line_chart(hist_df.set_index("cycle")[["nav"]], height=200)
        else:
            st.info("Accumulation des données NAV...")

    # Colonnes disponibles uniquement
    available_cols = [c for c in ["cycle", "price", "decision", "side", "confidence", "structural_S", "nav", "pnl"] if c in hist_df.columns]
    if available_cols:
        st.dataframe(
            hist_df[available_cols].tail(15),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# ── Contrôles ────────────────────────────────────────────────────────────────
st.subheader("⚙️ Contrôles")
ctrl1, ctrl2, ctrl3 = st.columns(3)
with ctrl1:
    if st.button("▶️ Cycle suivant", use_container_width=True):
        st.rerun()
with ctrl2:
    auto = st.toggle("🔄 Auto-refresh (5s)")
with ctrl3:
    if st.button("🔁 Reset session", use_container_width=True):
        for key in ["feed", "agents", "guard", "portfolio", "logger", "erc", "signer",
                    "identity", "history", "cycle_count", "trade_count"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

if auto:
    time.sleep(5)
    st.rerun()
