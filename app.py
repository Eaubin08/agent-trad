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
</style>
""", unsafe_allow_html=True)

# ─── Initialisation de l'état de session ────────────────────────────────────
# FIX: Portfolio prend initial_cash (pas initial_capital)
if "portfolio" not in st.session_state:
    st.session_state.portfolio = Portfolio(initial_cash=INITIAL_CAPITAL)
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
if "last_votes" not in st.session_state:
    st.session_state.last_votes = []
if "last_agg" not in st.session_state:
    st.session_state.last_agg = {}
if "history" not in st.session_state:
    st.session_state.history = []
# Feed persistant (pour l'historique des prix)
if "live_feed" not in st.session_state:
    st.session_state.live_feed = None
if "mock_feed" not in st.session_state:
    st.session_state.mock_feed = MockMarketFeed()
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
            "Tendance (drift)", -0.05, 0.05, float(st.session_state.drift_bias), 0.005,
            format="%.3f", help="Négatif = baissier, Positif = haussier"
        )
        st.session_state.vol_mult = st.slider(
            "Volatilité ×", 0.5, 5.0, float(st.session_state.vol_mult), 0.1,
            help="Multiplicateur de volatilité"
        )
        if st.button("⚡ Injecter Flash Crash", type="primary", use_container_width=True):
            st.session_state.flash_crash = True
            st.success("Flash crash injecté !")

    st.divider()
    st.markdown("### 🛡️ Guard X-108")
    st.session_state.guard_threshold = st.slider(
        "Seuil de sécurité θ_S", 0.3, 0.9,
        float(st.session_state.guard_threshold), 0.05,
        help="Plus élevé = plus restrictif"
    )
    st.session_state.guard.theta_S = st.session_state.guard_threshold

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Run", use_container_width=True, type="primary"):
            st.session_state.running = True
    with col2:
        if st.button("⏹ Stop", use_container_width=True):
            st.session_state.running = False

    st.divider()
    # FIX: as_dict() retourne 'nav' et 'realized_pnl', pas 'total_pnl'
    port_dict = st.session_state.portfolio.as_dict()
    st.metric("NAV", f"${port_dict['nav']:,.2f}")
    st.metric("PnL réalisé", f"${port_dict['realized_pnl']:+,.2f}")
    st.metric("Cycles", st.session_state.cycle_count)

# ─── Exécution d'un cycle ────────────────────────────────────────────────────
def run_one_cycle():
    # Récupérer ou créer le feed persistant
    if st.session_state.sim_mode:
        feed = st.session_state.mock_feed
        feed.drift_bias = st.session_state.drift_bias
        feed.volatility_multiplier = st.session_state.vol_mult
        if st.session_state.flash_crash:
            feed.flash_crash = True
            st.session_state.flash_crash = False
        market = feed.next()
    else:
        if st.session_state.live_feed is None:
            st.session_state.live_feed = LiveMarketFeed()
        feed = st.session_state.live_feed
        market = feed.next()
        if market is None:
            market = st.session_state.mock_feed.next()

    st.session_state.last_market = market

    # Votes des 14 agents
    votes = [a.vote(market) for a in st.session_state.agents]
    st.session_state.last_votes = votes
    agg = aggregate_votes(votes)
    st.session_state.last_agg = agg

    # Guard X-108 avec toutes les métriques réelles
    portfolio = st.session_state.portfolio
    guard_result = st.session_state.guard.evaluate(
        votes=votes,
        consensus=agg,
        snapshot_volatility=market.volatility,
        snapshot_event_risk=market.event_risk,
        exposure=portfolio.exposure(),
        drawdown=portfolio.state.drawdown,
        prediction_risk=market.volatility * 0.5,
    )
    st.session_state.last_decision = guard_result

    # Exécution du trade si ALLOW
    if guard_result.decision.value == "ALLOW":
        nav = portfolio.state.nav
        size = (nav * 0.02) / market.price if market.price > 0 else 0
        portfolio.apply(agg["side"], market.price, size, "ALLOW")
    else:
        portfolio.state.last_price = market.price

    # Proof log
    proof = st.session_state.logger.write({
        "cycle": st.session_state.cycle_count + 1,
        "market": {"price": market.price, "volatility": market.volatility},
        "consensus": agg,
        "guard": guard_result.validation_artifact,
    })

    st.session_state.cycle_count += 1
    port_dict = portfolio.as_dict()
    st.session_state.history.append({
        "cycle": st.session_state.cycle_count,
        "price": round(market.price, 2),
        "rsi": round(market.rsi, 1),
        "volatility": round(market.volatility, 3),
        "decision": guard_result.decision.value,
        "score_s": round(guard_result.structural_S, 3),
        "nav": round(port_dict["nav"], 2),
        "pnl": round(port_dict["realized_pnl"], 2),
        "hash": proof.get("hash", "")[:12],
    })
    if len(st.session_state.history) > 500:
        st.session_state.history = st.session_state.history[-500:]

    return market, agg, guard_result

# ─── Contenu de la page Home ─────────────────────────────────────────────────
st.title("🛡️ Obsidia — Trustless Multi-Agent Trading System")
st.caption(f"Agent `{AGENT_NAME}` · Version `{AGENT_VERSION}` · Réseau Sepolia (ERC-8004)")

# Exécution auto si running
if st.session_state.running:
    try:
        market, agg, guard_result = run_one_cycle()
    except Exception as e:
        st.error(f"Erreur cycle : {e}")
        market = st.session_state.last_market
        guard_result = st.session_state.last_decision
        agg = st.session_state.last_agg
    time.sleep(0.3)
    st.rerun()
elif st.session_state.last_market is None:
    try:
        market, agg, guard_result = run_one_cycle()
    except Exception as e:
        st.error(f"Erreur initialisation : {e}")
        market = None
        guard_result = None
        agg = None
else:
    market = st.session_state.last_market
    guard_result = st.session_state.last_decision
    agg = st.session_state.last_agg

# Garde défensive : si market est toujours None après le cycle initial, on stop
if market is None:
    st.warning("⚠️ Aucune donnée de marché disponible. Cliquez **▶ Run** dans la sidebar pour démarrer l'agent.")
    st.info("💡 L'agent va automatiquement basculer sur le mode simulation si Binance est indisponible.")
    st.stop()

# ─── KPIs principaux ─────────────────────────────────────────────────────────
port_dict = st.session_state.portfolio.as_dict()
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("💰 NAV", f"${port_dict['nav']:,.2f}",
              f"{port_dict['realized_pnl']:+,.2f}")
with col2:
    decision_icon = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}.get(
        guard_result.decision.value if guard_result else "HOLD", "🟡"
    )
    st.metric("🎯 Décision",
              f"{decision_icon} {guard_result.decision.value if guard_result else 'HOLD'}")
with col3:
    st.metric("📊 Score S",
              f"{guard_result.structural_S:.3f}" if guard_result else "—",
              f"seuil θ={st.session_state.guard_threshold:.2f}")
with col4:
    st.metric("💹 BTC Prix", f"${market.price:,.2f}" if market else "—",
              f"vol={market.volatility:.2f}" if market else "")
with col5:
    st.metric("🔄 Cycles", st.session_state.cycle_count)

st.divider()

# ─── Graphiques principaux ───────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Historique NAV & Prix")
    if len(st.session_state.history) >= 2:
        df = pd.DataFrame(st.session_state.history)
        # Normaliser pour afficher sur le même graphique
        df_chart = df.set_index("cycle")[["nav"]].copy()
        st.line_chart(df_chart, height=250)
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
    allows = int((df_all["decision"] == "ALLOW").sum())
    holds  = int((df_all["decision"] == "HOLD").sum())
    blocks = int((df_all["decision"] == "BLOCK").sum())

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

    avg_score = float(df_all["score_s"].mean())
    st.progress(min(1.0, avg_score), text=f"Score S moyen : {avg_score:.3f}")

    # Graphique volatilité
    if len(df_all) >= 2:
        st.subheader("📉 Volatilité & Score S")
        st.line_chart(df_all.set_index("cycle")[["volatility", "score_s"]], height=180)
