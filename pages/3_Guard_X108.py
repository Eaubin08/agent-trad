"""
Page 3 — Guard X-108 & Decision Flow
Affiche la décision de sécurité, le pipeline complet et les métriques de risque.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import time

from agents.registry import build_default_agents, aggregate_votes
from core.guard_x108 import GuardX108, GuardDecision
from core.live_market import MockMarketFeed, LiveMarketFeed

st.set_page_config(page_title="Guard X-108 — Obsidia", page_icon="🛡️", layout="wide")

st.title("🛡️ Guard X-108 — Moteur de Sécurité")
st.caption("Le Guard X-108 analyse chaque décision avant qu'elle ne soit envoyée au Risk Router ERC-8004.")

# ─── Initialisation ──────────────────────────────────────────────────────────
if "agents" not in st.session_state:
    st.session_state.agents = build_default_agents()
if "guard" not in st.session_state:
    st.session_state.guard = GuardX108()
if "guard_history" not in st.session_state:
    st.session_state.guard_history = []

sim_mode = st.session_state.get("sim_mode", True)
drift_bias = st.session_state.get("drift_bias", 0.0)
vol_mult = st.session_state.get("vol_mult", 1.0)
threshold = st.session_state.get("guard_threshold", 0.55)
st.session_state.guard.threshold = threshold

# ─── Récupération du cycle ────────────────────────────────────────────────────
def run_guard_cycle():
    if sim_mode:
        feed = MockMarketFeed(drift_bias=drift_bias, volatility_multiplier=vol_mult)
    else:
        feed = LiveMarketFeed()
    m = feed.get_state()
    if m is None:
        m = MockMarketFeed().get_state()

    votes = [a.vote(m) for a in st.session_state.agents]
    agg = aggregate_votes(votes)
    result = st.session_state.guard.evaluate(m, agg)
    return m, agg, result

if st.button("🔄 Analyser un nouveau cycle", type="primary"):
    m, agg, result = run_guard_cycle()
    st.session_state.guard_history.append({
        "cycle": len(st.session_state.guard_history) + 1,
        "decision": result.decision.value,
        "score_s": round(result.score_s, 3),
        "threshold": round(threshold, 2),
        "reason": result.reason[:60],
        "price": round(m.price, 2),
        "rsi": round(m.rsi, 1),
        "volatility": round(m.volatility, 4),
    })
    st.session_state.last_guard_result = result
    st.session_state.last_market_guard = m
    st.session_state.last_agg_guard = agg
elif "last_guard_result" not in st.session_state:
    m, agg, result = run_guard_cycle()
    st.session_state.last_guard_result = result
    st.session_state.last_market_guard = m
    st.session_state.last_agg_guard = agg

result = st.session_state.last_guard_result
market = st.session_state.last_market_guard
agg = st.session_state.last_agg_guard

st.divider()

# ─── Décision principale ─────────────────────────────────────────────────────
decision_styles = {
    "ALLOW": ("🟢", "#0d2818", "#2ea043", "Le Guard autorise l'exécution du trade."),
    "HOLD":  ("🟡", "#2d1f00", "#d29922", "Le Guard suspend la décision — conditions insuffisantes."),
    "BLOCK": ("🔴", "#2d0f0f", "#f85149", "Le Guard bloque le trade — risque trop élevé."),
}
icon, bg, border, msg = decision_styles.get(result.decision.value, decision_styles["HOLD"])

st.markdown(f"""
<div style="background:{bg}; border-left:6px solid {border}; padding:20px; border-radius:8px; margin-bottom:16px;">
    <h2 style="color:{border}; margin:0;">{icon} Décision : {result.decision.value}</h2>
    <p style="color:#c9d1d9; margin:8px 0 0;">{msg}</p>
    <p style="color:#8b949e; font-size:0.9rem; margin:4px 0 0;">Raison : {result.reason}</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Score S", f"{result.score_s:.3f}")
with col2:
    st.metric("Seuil θ_S", f"{threshold:.2f}")
with col3:
    st.metric("Marge", f"{result.score_s - threshold:+.3f}")
with col4:
    locked = getattr(result, "locked_until", None)
    st.metric("Verrou 108s", "🔒 Actif" if locked else "🔓 Libre")

st.divider()

# ─── Decision Flow — Pipeline 7 étapes ───────────────────────────────────────
st.subheader("🔄 Decision Flow — Pipeline Complet")
st.caption("Chaque étape est auditée et enregistrée dans le Validation Registry ERC-8004.")

steps = [
    ("1", "📊 Market Feed", f"BTC ${market.price:,.2f} · RSI {market.rsi:.1f} · Vol {market.volatility:.4f}", "DONE"),
    ("2", "🧠 14 Agents", f"Direction : {agg.direction} · Confiance : {agg.confidence:.1%}", "DONE"),
    ("3", "⚖️ Consensus", f"Votes agrégés · Poids normalisés", "DONE"),
    ("4", "🛡️ Guard X-108", f"Score S = {result.score_s:.3f} vs θ = {threshold:.2f}", "DONE"),
    ("5", "📝 Proof Hash", f"SHA-256 de la décision calculé", "DONE"),
    ("6", "⛓️ Validation Registry", f"Preuve soumise au contrat Sepolia", "PENDING" if result.decision.value == "ALLOW" else "SKIP"),
    ("7", "🚀 Risk Router", f"Trade exécuté" if result.decision.value == "ALLOW" else "Trade non exécuté", result.decision.value),
]

for step_num, step_name, step_detail, step_status in steps:
    status_color = {
        "DONE": "#2ea043", "PENDING": "#d29922", "SKIP": "#8b949e",
        "ALLOW": "#2ea043", "HOLD": "#d29922", "BLOCK": "#f85149"
    }.get(step_status, "#8b949e")
    status_icon = {
        "DONE": "✅", "PENDING": "⏳", "SKIP": "⏭️",
        "ALLOW": "✅", "HOLD": "⏳", "BLOCK": "🚫"
    }.get(step_status, "⚪")

    st.markdown(f"""
    <div style="display:flex; align-items:center; padding:10px; margin:4px 0; background:#161b22; border-radius:6px; border-left:3px solid {status_color};">
        <span style="font-size:1.2rem; margin-right:12px;">{status_icon}</span>
        <div style="flex:1;">
            <strong style="color:#c9d1d9;">Étape {step_num} — {step_name}</strong>
            <div style="color:#8b949e; font-size:0.85rem;">{step_detail}</div>
        </div>
        <span style="color:{status_color}; font-weight:600; font-size:0.85rem;">{step_status}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─── Métriques de risque ──────────────────────────────────────────────────────
st.subheader("📊 Métriques de Risque")
col_r1, col_r2 = st.columns(2)

with col_r1:
    st.markdown("**Score S — Décomposition**")
    from agents.indicators import structural_score
    score = structural_score(market)
    df_score = pd.DataFrame({
        "Composante": ["T (Trend)", "H (Harmony)", "A (Anomaly)", "S (Final)"],
        "Valeur": [
            score.get("T", 0),
            score.get("H", 0),
            score.get("A", 0),
            score.get("S", 0),
        ]
    })
    st.dataframe(df_score, use_container_width=True, hide_index=True)
    st.caption("Formule : S = 0.4·T + 0.4·H − 0.2·A (moteur Obsidia v18.3)")

with col_r2:
    st.markdown("**Historique des décisions Guard**")
    if st.session_state.guard_history:
        df_gh = pd.DataFrame(st.session_state.guard_history)
        decision_icons = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}
        df_gh["decision"] = df_gh["decision"].map(lambda d: f"{decision_icons.get(d, '⚪')} {d}")
        st.dataframe(
            df_gh[["cycle", "decision", "score_s", "threshold", "reason"]].tail(10)[::-1],
            use_container_width=True, hide_index=True
        )

# ─── Graphique historique Score S ────────────────────────────────────────────
if len(st.session_state.guard_history) >= 2:
    st.subheader("📈 Évolution du Score S")
    df_hist = pd.DataFrame(st.session_state.guard_history)
    df_chart = df_hist.set_index("cycle")[["score_s", "threshold"]].copy()
    st.line_chart(df_chart, height=200)
    st.caption("La ligne bleue (Score S) doit dépasser la ligne orange (seuil θ_S) pour qu'un trade soit autorisé.")
