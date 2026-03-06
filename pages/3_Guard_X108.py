"""
Page 3 — Guard X-108 & Decision Flow
Affiche la décision de sécurité, le pipeline complet et les métriques de risque.
Utilise l'état partagé de session (last_decision, last_market, history).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Guard X-108 — Obsidia", page_icon="🛡️", layout="wide")

st.title("🛡️ Guard X-108 — Moteur de Sécurité")
st.caption("Le Guard X-108 analyse chaque décision avant qu'elle ne soit envoyée au Risk Router ERC-8004.")

# ─── Vérification état session ───────────────────────────────────────────────
if "last_decision" not in st.session_state or st.session_state.last_decision is None:
    st.warning("⚠️ Aucune décision disponible. Lancez l'agent depuis la page **Home** (▶ Run).")
    st.stop()

result = st.session_state.last_decision
market = st.session_state.get("last_market")
agg = st.session_state.get("last_agg", {})
history = st.session_state.get("history", [])
threshold = st.session_state.get("guard_threshold", 0.55)

# ─── Décision principale ─────────────────────────────────────────────────────
decision_val = result.decision.value
dec_colors = {"ALLOW": "#2ea043", "HOLD": "#d29922", "BLOCK": "#f85149"}
dec_icons = {"ALLOW": "✅", "HOLD": "⏸️", "BLOCK": "🚫"}
dec_color = dec_colors.get(decision_val, "#8b949e")
dec_icon = dec_icons.get(decision_val, "❓")

st.markdown(f"""
<div style='background:#161b22;border:2px solid {dec_color};border-radius:12px;padding:24px;text-align:center;margin-bottom:20px'>
    <div style='font-size:3rem'>{dec_icon}</div>
    <div style='font-size:2.5rem;font-weight:800;color:{dec_color}'>{decision_val}</div>
    <div style='color:#8b949e;margin-top:8px'>{result.reason}</div>
</div>
""", unsafe_allow_html=True)

# ─── Métriques Guard ─────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    score_color = "🟢" if result.structural_S >= threshold else "🔴"
    st.metric(f"{score_color} Score S", f"{result.structural_S:.4f}")
with col2:
    st.metric("Seuil θ_S", f"{threshold:.2f}")
with col3:
    vol = market.volatility if market else 0
    vol_color = "🔴" if vol > 0.58 else "🟢"
    st.metric(f"{vol_color} Volatilité", f"{vol:.4f}")
with col4:
    er = market.event_risk if market else 0
    er_color = "🔴" if er > 0.88 else "🟢"
    st.metric(f"{er_color} Event Risk", f"{er:.4f}")
with col5:
    lock = getattr(result, "lock_active", getattr(result, "temporal_lock", False))
    st.metric("Verrou 108s", "🔒 ACTIF" if lock else "🔓 Libre")

st.divider()

# ─── Formule Guard X-108 ─────────────────────────────────────────────────────
st.subheader("🔢 Formule Guard X-108 (Obsidia OS2)")
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    st.markdown("""
    ```
    S = α·T + β·H − γ·A
    
    Où :
      T = Trend score    (momentum directionnel)
      H = Harmony score  (cohérence inter-agents)
      A = Anomaly score  (détection d'anomalie)
    
    Paramètres : α = 0.4, β = 0.35, γ = 0.25
    
    ALLOW  si S ≥ θ_S  ET  volatilité < 0.58  ET  event_risk < 0.88
    HOLD   si S ≥ θ_S  MAIS  conditions secondaires non remplies
    BLOCK  si S < θ_S  OU   volatilité ≥ 0.58  OU  event_risk ≥ 0.88
    ```
    """)
with col_f2:
    if market:
        from agents.indicators import structural_score
        score = structural_score(market)
        st.metric("T (Trend)", f"{score.get('T', 0):.4f}")
        st.metric("H (Harmony)", f"{score.get('H', 0):.4f}")
        st.metric("A (Anomaly)", f"{score.get('A', 0):.4f}")
        st.metric("S (Final)", f"{score.get('S', 0):.4f}")

st.divider()

# ─── Decision Flow 7 étapes ──────────────────────────────────────────────────
st.subheader("🔄 Decision Flow — Pipeline complet")

steps = [
    ("1", "Market Feed", "Binance API ou Mock", "✅ OK", "#2ea043"),
    ("2", "14 Agents", f"Consensus : {agg.get('side', '—')} ({agg.get('confidence', 0):.0%})", "✅ OK", "#2ea043"),
    ("3", "Agrégation", f"Buy: {agg.get('buy_weight', 0):.2f} | Sell: {agg.get('sell_weight', 0):.2f}", "✅ OK", "#2ea043"),
    ("4", "Guard X-108", f"Score S = {result.structural_S:.4f} | Seuil = {threshold:.2f}", "✅ OK", "#2ea043"),
    ("5", "Décision", result.reason, f"{dec_icon} {decision_val}", dec_color),
    ("6", "EIP-712 Sign", "Signature TradeIntent (stub mode)", "🟡 Stub", "#d29922"),
    ("7", "Risk Router", "Envoi au contrat Sepolia", "🟡 Stub", "#d29922"),
]

for step in steps:
    num, name, detail, status, color = step
    st.markdown(f"""
    <div style='display:flex;align-items:center;background:#161b22;border-left:4px solid {color};
                border-radius:4px;padding:10px 16px;margin-bottom:6px'>
        <div style='font-size:1.2rem;font-weight:700;color:{color};min-width:32px'>{num}</div>
        <div style='flex:1;margin:0 16px'>
            <div style='font-weight:600;color:#c9d1d9'>{name}</div>
            <div style='font-size:0.8rem;color:#8b949e'>{detail}</div>
        </div>
        <div style='font-size:0.85rem;color:{color};font-weight:600'>{status}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─── Historique des décisions Guard ──────────────────────────────────────────
if len(history) >= 2:
    st.subheader("📈 Historique des décisions")
    df_h = pd.DataFrame(history)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**Score S vs Seuil θ_S**")
        df_score = df_h.set_index("cycle")[["score_s"]].copy() if "score_s" in df_h.columns else df_h.set_index("cycle")[["nav"]].copy()
        df_score["Seuil θ_S"] = threshold
        st.line_chart(df_score, height=200)
    with col_g2:
        st.markdown("**Volatilité vs Seuil (0.58)**")
        df_vol = df_h.set_index("cycle")[["volatility"]].copy()
        df_vol["Seuil volatilité"] = 0.58
        st.area_chart(df_vol, height=200)

    # Tableau des décisions
    st.markdown("**Dernières décisions**")
    cols_dec = [c for c in ["cycle", "price", "score_s", "volatility", "decision"] if c in df_h.columns]
    df_dec = df_h[cols_dec].tail(15)[::-1].copy()
    decision_icons = {"ALLOW": "✅ ALLOW", "HOLD": "⏸️ HOLD", "BLOCK": "🚫 BLOCK"}
    df_dec["decision"] = df_dec["decision"].map(lambda d: decision_icons.get(d, d))
    st.dataframe(df_dec, width="stretch", hide_index=True)
else:
    st.info("Accumulez des cycles depuis **Home** pour voir l'historique.")
