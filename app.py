"""
Obsidia — Trustless Multi-Agent Trading System
Page principale : Dashboard Home
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import time
import pandas as pd

from agents.indicators import MarketState
from agents.registry import build_default_agents, aggregate_votes
from core.guard_x108 import GuardX108
from core.live_market import MockMarketFeed, LiveMarketFeed
from core.portfolio import Portfolio
from core.logger import ProofLogger
from config.settings import INITIAL_CAPITAL, AGENT_NAME, AGENT_VERSION

# ─── Configuration de la page ───────────────────────────────────────────────
st.set_page_config(
    page_title="Obsidia — Trading Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS global ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #0d1117; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
.metric-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; }
.metric-value { font-size: 1.8rem; font-weight: 700; color: #58a6ff; }
.metric-label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; }
.decision-allow { background: #0d2818; border-left: 4px solid #2ea043; padding: 12px; border-radius: 4px; }
.decision-hold  { background: #2d1f00; border-left: 4px solid #d29922; padding: 12px; border-radius: 4px; }
.decision-block { background: #2d0f0f; border-left: 4px solid #f85149; padding: 12px; border-radius: 4px; }
.agent-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin: 2px; }
</style>
""", unsafe_allow_html=True)

# ─── Initialisation de l'état de session ────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
if "logger" not in st.session_state:
    st.session_state.logger = ProofLogger()
if "guard" not in st.session_state:
    st.session_state.guard = GuardX108()
if "agents" not in st.session_state:
    st.session_state.agents = build_default_agents()
if "cycle_count" not in st.session_state:
    st.session_state.cycle_count = 0
if "last_decision" not in st.session_state:
    st.session_state.last_decision = None
if "last_market" not in st.session_state:
    st.session_state.last_market = None
if "history" not in st.session_state:
    st.session_state.history = []
# Paramètres de simulation (partagés entre pages)
if "sim_mode" not in st.session_state:
    st.session_state.sim_mode = True
if "drift_bias" not in st.session_state:
    st.session_state.drift_bias = 0.0
if "vol_mult" not in st.session_state:
    st.session_state.vol_mult = 1.0
if "flash_crash" not in st.session_state:
    st.session_state.flash_crash = False
if "guard_threshold" not in st.session_state:
    st.session_state.guard_threshold = 0.55
if "running" not in st.session_state:
    st.session_state.running = False

# ─── Sidebar partagée ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Obsidia")
    st.markdown(f"`{AGENT_NAME}` · `v{AGENT_VERSION}`")
    st.divider()

    st.markdown("### ⚙️ Mode")
    st.session_state.sim_mode = st.toggle(
        "🔬 Mode Simulation",
        value=st.session_state.sim_mode,
        help="Désactivez pour utiliser les données Binance live"
    )

    if st.session_state.sim_mode:
        st.markdown("### 📊 Marché simulé")
        st.session_state.drift_bias = st.slider(
            "Tendance (drift)", -0.05, 0.05, st.session_state.drift_bias, 0.005,
            format="%.3f", help="Négatif = baissier, Positif = haussier"
        )
        st.session_state.vol_mult = st.slider(
            "Volatilité ×", 0.5, 5.0, st.session_state.vol_mult, 0.1,
            help="Multiplicateur de volatilité"
        )
        if st.button("⚡ Injecter Flash Crash", type="primary", use_container_width=True):
            st.session_state.flash_crash = True
            st.success("Flash crash injecté !")

    st.divider()
    st.markdown("### 🛡️ Guard X-108")
    st.session_state.guard_threshold = st.slider(
        "Seuil de sécurité θ_S", 0.3, 0.9,
        st.session_state.guard_threshold, 0.05,
        help="Plus élevé = plus restrictif"
    )
    st.session_state.guard.threshold = st.session_state.guard_threshold

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Run", use_container_width=True, type="primary"):
            st.session_state.running = True
    with col2:
        if st.button("⏹ Stop", use_container_width=True):
            st.session_state.running = False

    st.divider()
    nav = st.session_state.portfolio.as_dict()
    st.metric("NAV", f"${nav['nav']:,.2f}")
    st.metric("PnL", f"${nav['total_pnl']:+,.2f}")
    st.metric("Cycles", st.session_state.cycle_count)

# ─── Exécution d'un cycle ────────────────────────────────────────────────────
def run_one_cycle():
    if st.session_state.sim_mode:
        feed = MockMarketFeed(
            drift_bias=st.session_state.drift_bias,
            volatility_multiplier=st.session_state.vol_mult,
        )
        if st.session_state.flash_crash:
            feed.inject_flash_crash()
            st.session_state.flash_crash = False
    else:
        feed = LiveMarketFeed()

    market = feed.get_state()
    if market is None:
        feed = MockMarketFeed()
        market = feed.get_state()

    st.session_state.last_market = market

    votes = [a.vote(market) for a in st.session_state.agents]
    agg = aggregate_votes(votes)
    guard_result = st.session_state.guard.evaluate(market, agg)
    st.session_state.last_decision = guard_result

    portfolio = st.session_state.portfolio
    if guard_result.decision.value == "ALLOW":
        size = portfolio.nav * 0.02
        portfolio.apply(guard_result.decision.value, market.price, size)

    proof = st.session_state.logger.log(market, agg, guard_result)

    st.session_state.cycle_count += 1
    nav = portfolio.as_dict()
    st.session_state.history.append({
        "cycle": st.session_state.cycle_count,
        "price": round(market.price, 2),
        "rsi": round(market.rsi, 1),
        "decision": guard_result.decision.value,
        "score_s": round(guard_result.score_s, 3),
        "nav": round(nav["nav"], 2),
        "pnl": round(nav["total_pnl"], 2),
        "hash": proof.get("artifact_hash", "")[:12],
    })
    if len(st.session_state.history) > 200:
        st.session_state.history = st.session_state.history[-200:]

    return market, agg, guard_result

# ─── Contenu de la page Home ─────────────────────────────────────────────────
st.title("🛡️ Obsidia — Trustless Multi-Agent Trading System")
st.caption(f"Agent `{AGENT_NAME}` · Version `{AGENT_VERSION}` · Réseau Sepolia (ERC-8004)")

# Exécution auto si running
if st.session_state.running:
    market, agg, guard_result = run_one_cycle()
    time.sleep(0.1)
    st.rerun()
elif st.session_state.last_market is None:
    # Premier cycle au chargement
    market, agg, guard_result = run_one_cycle()
else:
    market = st.session_state.last_market
    guard_result = st.session_state.last_decision

# ─── KPIs principaux ─────────────────────────────────────────────────────────
nav = st.session_state.portfolio.as_dict()
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("💰 NAV", f"${nav['nav']:,.2f}", f"{nav['total_pnl']:+,.2f}")
with col2:
    decision_color = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}.get(
        guard_result.decision.value if guard_result else "HOLD", "🟡"
    )
    st.metric("🎯 Décision", f"{decision_color} {guard_result.decision.value if guard_result else 'HOLD'}")
with col3:
    st.metric("📊 Score S", f"{guard_result.score_s:.3f}" if guard_result else "—",
              f"seuil θ={st.session_state.guard_threshold:.2f}")
with col4:
    st.metric("💹 BTC Prix", f"${market.price:,.2f}" if market else "—")
with col5:
    st.metric("🔄 Cycles", st.session_state.cycle_count)

st.divider()

# ─── Résumé des dernières décisions ─────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Historique NAV")
    if len(st.session_state.history) >= 2:
        df = pd.DataFrame(st.session_state.history)
        st.line_chart(df.set_index("cycle")[["nav", "price"]], height=250)
    else:
        st.info("Lancez l'agent (▶ Run) pour voir l'historique.")

with col_right:
    st.subheader("🎯 Dernières décisions")
    if st.session_state.history:
        df_hist = pd.DataFrame(st.session_state.history[-10:][::-1])
        decision_icons = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}
        df_display = df_hist[["cycle", "price", "decision", "score_s"]].copy()
        df_display["decision"] = df_display["decision"].map(
            lambda d: f"{decision_icons.get(d, '⚪')} {d}"
        )
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune décision encore.")

st.divider()

# ─── Statistiques de session ─────────────────────────────────────────────────
if st.session_state.history:
    df_all = pd.DataFrame(st.session_state.history)
    total = len(df_all)
    allows = (df_all["decision"] == "ALLOW").sum()
    holds  = (df_all["decision"] == "HOLD").sum()
    blocks = (df_all["decision"] == "BLOCK").sum()

    st.subheader("📊 Statistiques de session")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total cycles", total)
    with c2:
        st.metric("🟢 ALLOW", f"{allows} ({allows/total*100:.0f}%)")
    with c3:
        st.metric("🟡 HOLD", f"{holds} ({holds/total*100:.0f}%)")
    with c4:
        st.metric("🔴 BLOCK", f"{blocks} ({blocks/total*100:.0f}%)")

    # Score S moyen
    avg_score = df_all["score_s"].mean()
    st.progress(float(avg_score), text=f"Score S moyen : {avg_score:.3f}")
