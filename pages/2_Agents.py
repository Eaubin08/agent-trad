"""
Page 2 — Agents
Constellation des 14 agents avec votes réels, consensus et Deep Dive par agent.
Utilise l'état partagé de session (last_votes, last_agg, last_market).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Agents — Obsidia", page_icon="🧠", layout="wide")

st.title("🧠 Constellation des 14 Agents")
st.caption("Chaque agent vote indépendamment. Le Guard X-108 valide le consensus avant tout trade.")

# ─── Vérification état session ───────────────────────────────────────────────
if "last_votes" not in st.session_state or not st.session_state.last_votes:
    st.warning("⚠️ Aucun vote disponible. Lancez l'agent depuis la page **Home** (▶ Run).")
    st.info("💡 Allez sur la page **Home**, cliquez **▶ Run**, puis revenez ici.")
    st.stop()

votes = st.session_state.last_votes
agg = st.session_state.get("last_agg", {})
market = st.session_state.get("last_market")
guard_result = st.session_state.get("last_decision")
history = st.session_state.get("history", [])

# ─── Consensus global ────────────────────────────────────────────────────────
st.subheader("🎯 Consensus pondéré")
col1, col2, col3, col4 = st.columns(4)

buy_w = agg.get("buy_weight", 0)
sell_w = agg.get("sell_weight", 0)
hold_w = agg.get("hold_weight", 0)
total_w = buy_w + sell_w + hold_w

with col1:
    side_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(agg.get("side", "HOLD"), "🟡")
    st.metric("Signal dominant", f"{side_icon} {agg.get('side', '—')}")
with col2:
    st.metric("Confiance", f"{agg.get('confidence', 0):.1%}")
with col3:
    buy_c = sum(1 for v in votes if v.signal == "BUY")
    sell_c = sum(1 for v in votes if v.signal == "SELL")
    hold_c = sum(1 for v in votes if v.signal == "HOLD")
    st.metric("Votes", f"🟢{buy_c} 🔴{sell_c} 🟡{hold_c}")
with col4:
    if guard_result:
        dec_icon = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}.get(guard_result.decision.value, "🟡")
        st.metric("Décision Guard", f"{dec_icon} {guard_result.decision.value}")

st.progress(min(1.0, agg.get("confidence", 0)), text=f"Confiance globale : {agg.get('confidence', 0):.1%}")

st.divider()

# ─── Tableau des 14 agents ────────────────────────────────────────────────────
st.subheader("📊 Votes des 14 agents")

rows = []
for v in votes:
    signal_icon = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "HOLD": "🟡 HOLD"}.get(v.signal, v.signal)
    rows.append({
        "Agent": v.name,
        "Famille": v.category,
        "Signal": signal_icon,
        "Confiance": f"{v.confidence:.1%}",
        "Raisonnement": v.rationale[:90] + "..." if len(v.rationale) > 90 else v.rationale,
    })

df_votes = pd.DataFrame(rows)

def color_signal(val):
    if "BUY" in str(val):
        return "color: #2ea043; font-weight: bold"
    elif "SELL" in str(val):
        return "color: #f85149; font-weight: bold"
    return "color: #d29922"

styled = df_votes.style.map(color_signal, subset=["Signal"])
st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ─── Répartition par famille ──────────────────────────────────────────────────
st.subheader("👨‍👩‍👧‍👦 Répartition par famille")
families: dict = {}
for v in votes:
    fam = v.category
    if fam not in families:
        families[fam] = {"BUY": 0, "SELL": 0, "HOLD": 0}
    families[fam][v.signal] = families[fam].get(v.signal, 0) + 1

cols_fam = st.columns(max(1, len(families)))
for i, (fam, counts) in enumerate(families.items()):
    with cols_fam[i]:
        st.markdown(f"**{fam.upper()}**")
        st.markdown(f"🟢 BUY: **{counts.get('BUY', 0)}**")
        st.markdown(f"🔴 SELL: **{counts.get('SELL', 0)}**")
        st.markdown(f"🟡 HOLD: **{counts.get('HOLD', 0)}**")

st.divider()

# ─── Deep Dive par agent ──────────────────────────────────────────────────────
st.subheader("🔬 Deep Dive — Raisonnement d'un agent")

agent_names_list = [v.name for v in votes]
selected = st.selectbox("Sélectionnez un agent :", agent_names_list)

if selected and market:
    v_sel = next((v for v in votes if v.name == selected), None)
    if v_sel:
        col_info, col_chart = st.columns([1, 2])
        with col_info:
            signal_color = {"BUY": "#2ea043", "SELL": "#f85149", "HOLD": "#d29922"}.get(v_sel.signal, "#8b949e")
            st.markdown(f"""
            <div style='background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px'>
                <div style='font-size:0.75rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.05em'>Signal</div>
                <div style='font-size:2rem;font-weight:700;color:{signal_color}'>{v_sel.signal}</div>
                <div style='font-size:0.75rem;color:#8b949e;margin-top:8px'>Confiance</div>
                <div style='font-size:1.4rem;font-weight:600;color:#58a6ff'>{v_sel.confidence:.1%}</div>
                <div style='font-size:0.75rem;color:#8b949e;margin-top:8px'>Famille</div>
                <div style='color:#c9d1d9'>{v_sel.category}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**📝 Raisonnement :**")
            st.info(v_sel.rationale)

            # Données brutes utilisées par l'agent
            st.markdown("**📊 Données brutes :**")
            data_rows = [
                ("Prix actuel", f"${market.price:,.2f}"),
                ("RSI (14)", f"{market.rsi:.1f}"),
                ("Volatilité", f"{market.volatility:.4f}"),
                ("Event Risk", f"{market.event_risk:.4f}"),
                ("OBI", f"{market.order_book_imbalance:+.4f}"),
                ("Sentiment", f"{market.sentiment_score:+.4f}"),
            ]
            if market.sma20:
                data_rows.append(("SMA 20", f"${market.sma20:,.2f}"))
            if market.sma50:
                data_rows.append(("SMA 50", f"${market.sma50:,.2f}"))
            df_data = pd.DataFrame(data_rows, columns=["Indicateur", "Valeur"])
            st.dataframe(df_data, use_container_width=True, hide_index=True)

        with col_chart:
            # Formule mathématique
            formulas = {
                "MarketDataAgent": "signal = BUY si Δprix > 0.1% | SELL si Δprix < -0.1% | HOLD",
                "RSIAgent": "RSI(14) = 100 - 100/(1+RS) | BUY si RSI < 35 | SELL si RSI > 65",
                "MACDAgent": "MACD = EMA(12) - EMA(26) | BUY si MACD > Signal | SELL sinon",
                "BollingerAgent": "BB = SMA(20) ± 2σ | BUY si prix < BB_low | SELL si prix > BB_up",
                "ATRAgent": "ATR(14) = EMA(True Range, 14) | HOLD si ATR/prix > 3%",
                "ZScoreAgent": "Z = (prix - μ) / σ | BUY si Z < -1.5 | SELL si Z > 1.5",
                "VolumeAgent": "vol_ratio = volume / vol_moy(20) | BUY si ratio > 1.5",
                "SentimentAgent": "sentiment ∈ [-1, 1] | BUY si > 0.3 | SELL si < -0.3",
                "EventRiskAgent": "event_risk ∈ [0, 1] | BLOCK si > 0.88 | HOLD si > 0.6",
                "OrderBookAgent": "OBI = (bid_qty - ask_qty) / total | BUY si OBI > 0.15",
                "TrendAgent": "trend = SMA20 vs SMA50 | BUY si SMA20 > SMA50 (golden cross)",
                "MomentumAgent": "momentum = prix(t) / prix(t-10) - 1 | BUY si > 0.5%",
                "PortfolioAgent": "exposure = base_units × prix / NAV | SELL si exposure > 80%",
                "RiskAgent": "drawdown = (peak_NAV - NAV) / peak_NAV | BLOCK si > 15%",
                "SignalAggregatorAgent": "S = α·T + β·H − γ·A (Obsidia OS2 structural score)",
            }
            formula = formulas.get(v_sel.name, "Formule propriétaire Obsidia v18.3")
            st.markdown(f"**🔢 Formule :** `{formula}`")

            # Graphique historique si disponible
            if len(history) >= 2:
                df_h = pd.DataFrame(history)
                if v_sel.category in ("technical", "strategy"):
                    st.markdown("**📈 Prix + RSI (historique)**")
                    st.line_chart(df_h.set_index("cycle")[["price"]], height=160)
                    st.line_chart(df_h.set_index("cycle")[["rsi"]], height=120)
                    st.caption("🔴 RSI > 70 = Suracheté | 🟢 RSI < 30 = Survendu")
                elif v_sel.category == "observation":
                    st.markdown("**📊 Prix + Volatilité (historique)**")
                    st.line_chart(df_h.set_index("cycle")[["price"]], height=160)
                    st.area_chart(df_h.set_index("cycle")[["volatility"]], height=120)
                else:
                    st.markdown("**📈 NAV + Score S (historique)**")
                    st.line_chart(df_h.set_index("cycle")[["nav"]], height=160)
                    st.line_chart(df_h.set_index("cycle")[["score_s"]], height=120)
                    st.caption(f"Seuil θ_S = {st.session_state.get('guard_threshold', 0.55):.2f}")
            else:
                st.info("Accumulez des cycles depuis **Home** pour voir les graphiques.")
