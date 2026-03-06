"""
Page 4 — Strategy Lab
Simulation Monte Carlo, comparaison de stratégies et prévision de marché.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import random
import math

st.set_page_config(page_title="Strategy Lab — Obsidia", page_icon="🎯", layout="wide")

st.title("🎯 Strategy Lab — Simulation & Entraînement")
st.caption("Testez vos hypothèses, comparez des stratégies et entraînez-vous avant de confier vos décisions à l'agent.")

# ─── Onglets ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "💰 Simuler un investissement",
    "⚔️ Comparer des stratégies",
    "🔮 Prévoir & Adapter"
])

# ═══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — Simuler un investissement
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("💰 Simuler un investissement")
    st.caption("Entrez vos paramètres. Le système lance 1 000 scénarios Monte Carlo et vous montre la distribution des résultats.")

    col_params, col_results = st.columns([1, 2])

    with col_params:
        st.markdown("**Paramètres de l'investissement**")

        asset = st.selectbox("Actif", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"], key="sim_asset")
        capital = st.number_input("Capital investi ($)", min_value=100, max_value=1_000_000,
                                   value=10_000, step=500, key="sim_capital")
        duration_days = st.slider("Durée (jours)", 7, 365, 30, key="sim_duration")
        strategy = st.selectbox("Stratégie", [
            "Momentum (suivre la tendance)",
            "Mean Reversion (retour à la moyenne)",
            "Hold (conserver)",
            "DCA (achat progressif)",
            "Guard-Driven (laisser l'agent décider)",
        ], key="sim_strategy")

        st.markdown("**Hypothèses de marché**")
        expected_return = st.slider("Rendement annuel attendu (%)", -50, 100, 15, key="sim_return") / 100
        expected_vol = st.slider("Volatilité annuelle (%)", 5, 150, 60, key="sim_vol") / 100

        n_simulations = 1000
        run_sim = st.button("🚀 Lancer la simulation", type="primary", use_container_width=True, key="run_sim1")

    with col_results:
        if run_sim or "sim_results" in st.session_state:
            if run_sim:
                # Simulation Monte Carlo
                dt = 1 / 365
                mu = expected_return
                sigma = expected_vol

                # Ajustement selon la stratégie
                strategy_multipliers = {
                    "Momentum (suivre la tendance)": (1.1, 1.2),
                    "Mean Reversion (retour à la moyenne)": (0.9, 0.8),
                    "Hold (conserver)": (1.0, 1.0),
                    "DCA (achat progressif)": (1.05, 0.9),
                    "Guard-Driven (laisser l'agent décider)": (1.08, 0.85),
                }
                ret_mult, vol_mult = strategy_multipliers.get(strategy, (1.0, 1.0))
                mu_adj = mu * ret_mult
                sigma_adj = sigma * vol_mult

                final_values = []
                paths_sample = []  # 20 chemins pour visualisation

                for i in range(n_simulations):
                    price = capital
                    path = [price]
                    for _ in range(duration_days):
                        shock = np.random.normal(0, 1)
                        price *= math.exp((mu_adj - 0.5 * sigma_adj**2) * dt + sigma_adj * math.sqrt(dt) * shock)
                        path.append(price)
                    final_values.append(price)
                    if i < 20:
                        paths_sample.append(path)

                final_values = sorted(final_values)
                p5  = np.percentile(final_values, 5)
                p25 = np.percentile(final_values, 25)
                p50 = np.percentile(final_values, 50)
                p75 = np.percentile(final_values, 75)
                p95 = np.percentile(final_values, 95)
                prob_profit = sum(1 for v in final_values if v > capital) / n_simulations

                st.session_state.sim_results = {
                    "p5": p5, "p25": p25, "p50": p50, "p75": p75, "p95": p95,
                    "prob_profit": prob_profit, "paths": paths_sample,
                    "capital": capital, "strategy": strategy,
                    "duration": duration_days, "asset": asset,
                    "final_values": final_values,
                }

            res = st.session_state.sim_results

            # Métriques clés
            st.markdown("**Résultats sur 1 000 scénarios**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("🐻 Pire cas (5%)", f"${res['p5']:,.0f}",
                          f"{(res['p5']/res['capital']-1)*100:+.1f}%")
                st.metric("📊 Médiane (50%)", f"${res['p50']:,.0f}",
                          f"{(res['p50']/res['capital']-1)*100:+.1f}%")
            with c2:
                st.metric("🎯 Cas probable (75%)", f"${res['p75']:,.0f}",
                          f"{(res['p75']/res['capital']-1)*100:+.1f}%")
                st.metric("🚀 Meilleur cas (95%)", f"${res['p95']:,.0f}",
                          f"{(res['p95']/res['capital']-1)*100:+.1f}%")
            with c3:
                prob_color = "🟢" if res["prob_profit"] > 0.6 else ("🟡" if res["prob_profit"] > 0.4 else "🔴")
                st.metric(f"{prob_color} Probabilité de profit", f"{res['prob_profit']:.1%}")
                max_loss = (res['p5'] / res['capital'] - 1) * 100
                st.metric("⚠️ Perte max (5%)", f"{max_loss:.1f}%")

            # Graphique des chemins simulés
            st.markdown("**20 chemins simulés (sur 1 000)**")
            if res["paths"]:
                df_paths = pd.DataFrame(res["paths"]).T
                df_paths.columns = [f"Scénario {i+1}" for i in range(len(res["paths"]))]
                # Garder seulement quelques colonnes pour la lisibilité
                st.line_chart(df_paths.iloc[:, :10], height=250)
                st.caption(f"Chaque ligne = un scénario possible pour {res['asset']} sur {res['duration']} jours")

            # Distribution finale
            st.markdown("**Distribution des valeurs finales**")
            bins = 30
            hist_vals, bin_edges = np.histogram(res["final_values"], bins=bins)
            df_hist = pd.DataFrame({
                "Valeur finale ($)": [f"${(bin_edges[i]+bin_edges[i+1])/2:,.0f}" for i in range(bins)],
                "Fréquence": hist_vals,
            })
            st.bar_chart(df_hist.set_index("Valeur finale ($)"), height=200)

            # Recommandation Guard
            st.divider()
            st.markdown("**🛡️ Analyse Guard X-108**")
            if res["prob_profit"] > 0.65 and res["p5"] / res["capital"] > 0.8:
                st.success(f"✅ **ALLOW** — Le Guard X-108 autoriserait cette stratégie. Probabilité de profit : {res['prob_profit']:.1%}, perte max limitée à {abs(res['p5']/res['capital']-1)*100:.1f}%.")
            elif res["prob_profit"] > 0.5:
                st.warning(f"⏳ **HOLD** — Le Guard X-108 suspendrait cette stratégie. Les conditions sont incertaines. Probabilité de profit : {res['prob_profit']:.1%}.")
            else:
                st.error(f"🚫 **BLOCK** — Le Guard X-108 bloquerait cette stratégie. Risque trop élevé. Probabilité de profit : {res['prob_profit']:.1%}.")
        else:
            st.info("👆 Configurez vos paramètres et cliquez sur **Lancer la simulation** pour voir les résultats.")

# ═══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — Comparer des stratégies
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("⚔️ Comparer des stratégies")
    st.caption("Mettez 2 stratégies en compétition sur les mêmes données de marché simulées.")

    col_cmp1, col_cmp2 = st.columns(2)
    with col_cmp1:
        strat_a = st.selectbox("Stratégie A", [
            "Momentum", "Mean Reversion", "Hold", "DCA", "Guard-Driven"
        ], index=0, key="cmp_a")
        risk_a = st.slider("Tolérance au risque A (%)", 1, 50, 20, key="risk_a")

    with col_cmp2:
        strat_b = st.selectbox("Stratégie B", [
            "Momentum", "Mean Reversion", "Hold", "DCA", "Guard-Driven"
        ], index=1, key="cmp_b")
        risk_b = st.slider("Tolérance au risque B (%)", 1, 50, 10, key="risk_b")

    cmp_capital = st.number_input("Capital de départ ($)", 1000, 100_000, 10_000, 1000, key="cmp_capital")
    cmp_days = st.slider("Durée de la simulation (jours)", 30, 365, 90, key="cmp_days")

    if st.button("⚔️ Lancer la comparaison", type="primary", use_container_width=True, key="run_cmp"):
        def simulate_strategy(name, risk_pct, capital, days, seed=42):
            np.random.seed(seed)
            nav = capital
            max_nav = capital
            max_drawdown = 0
            pnl_history = [capital]
            decisions = {"ALLOW": 0, "HOLD": 0, "BLOCK": 0}

            strat_params = {
                "Momentum": (0.0003, 0.02),
                "Mean Reversion": (-0.0001, 0.015),
                "Hold": (0.0001, 0.005),
                "DCA": (0.0002, 0.012),
                "Guard-Driven": (0.00025, 0.018),
            }
            mu_d, sigma_d = strat_params.get(name, (0.0002, 0.015))
            risk_limit = risk_pct / 100

            for _ in range(days):
                ret = np.random.normal(mu_d, sigma_d)
                # Guard simulé
                vol_shock = abs(np.random.normal(0, sigma_d))
                if vol_shock > risk_limit * 0.8:
                    decisions["BLOCK"] += 1
                    continue
                elif vol_shock > risk_limit * 0.4:
                    decisions["HOLD"] += 1
                    nav *= (1 + ret * 0.3)
                else:
                    decisions["ALLOW"] += 1
                    nav *= (1 + ret)

                pnl_history.append(nav)
                if nav > max_nav:
                    max_nav = nav
                dd = (max_nav - nav) / max_nav
                if dd > max_drawdown:
                    max_drawdown = dd

            return {
                "name": name,
                "final_nav": nav,
                "pnl": nav - capital,
                "pnl_pct": (nav / capital - 1) * 100,
                "max_drawdown": max_drawdown * 100,
                "decisions": decisions,
                "history": pnl_history,
            }

        res_a = simulate_strategy(strat_a, risk_a, cmp_capital, cmp_days, seed=42)
        res_b = simulate_strategy(strat_b, risk_b, cmp_capital, cmp_days, seed=42)
        st.session_state.cmp_results = (res_a, res_b)

    if "cmp_results" in st.session_state:
        res_a, res_b = st.session_state.cmp_results

        # Tableau comparatif
        st.markdown("**Résultats comparatifs**")
        winner = res_a["name"] if res_a["final_nav"] > res_b["final_nav"] else res_b["name"]
        st.success(f"🏆 Gagnant : **{winner}**")

        df_cmp = pd.DataFrame([
            {
                "Métrique": "NAV finale ($)",
                res_a["name"]: f"${res_a['final_nav']:,.2f}",
                res_b["name"]: f"${res_b['final_nav']:,.2f}",
            },
            {
                "Métrique": "PnL (%)",
                res_a["name"]: f"{res_a['pnl_pct']:+.2f}%",
                res_b["name"]: f"{res_b['pnl_pct']:+.2f}%",
            },
            {
                "Métrique": "Drawdown max (%)",
                res_a["name"]: f"{res_a['max_drawdown']:.2f}%",
                res_b["name"]: f"{res_b['max_drawdown']:.2f}%",
            },
            {
                "Métrique": "Trades ALLOW",
                res_a["name"]: res_a["decisions"]["ALLOW"],
                res_b["name"]: res_b["decisions"]["ALLOW"],
            },
            {
                "Métrique": "Trades BLOCK (Guard)",
                res_a["name"]: res_a["decisions"]["BLOCK"],
                res_b["name"]: res_b["decisions"]["BLOCK"],
            },
        ])
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)

        # Graphique NAV comparatif
        st.markdown("**Évolution de la NAV**")
        max_len = max(len(res_a["history"]), len(res_b["history"]))
        hist_a = res_a["history"] + [res_a["history"][-1]] * (max_len - len(res_a["history"]))
        hist_b = res_b["history"] + [res_b["history"][-1]] * (max_len - len(res_b["history"]))
        df_nav = pd.DataFrame({
            res_a["name"]: hist_a,
            res_b["name"]: hist_b,
        })
        st.line_chart(df_nav, height=300)

        # Décisions Guard
        st.markdown("**Répartition des décisions Guard X-108**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"**{res_a['name']}**")
            total_a = sum(res_a["decisions"].values())
            for dec, cnt in res_a["decisions"].items():
                icon = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}.get(dec, "⚪")
                pct = cnt / total_a * 100 if total_a > 0 else 0
                st.markdown(f"{icon} {dec}: **{cnt}** ({pct:.0f}%)")
        with col_d2:
            st.markdown(f"**{res_b['name']}**")
            total_b = sum(res_b["decisions"].values())
            for dec, cnt in res_b["decisions"].items():
                icon = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}.get(dec, "⚪")
                pct = cnt / total_b * 100 if total_b > 0 else 0
                st.markdown(f"{icon} {dec}: **{cnt}** ({pct:.0f}%)")
    else:
        st.info("👆 Configurez les deux stratégies et lancez la comparaison.")

# ═══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — Prévoir & Adapter
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔮 Prévoir le marché & Adapter la stratégie")
    st.caption("Entrez vos hypothèses sur le marché. Le système vous dit quelle stratégie est la mieux adaptée et quel est le risque Guard.")

    col_hyp, col_rec = st.columns([1, 1])

    with col_hyp:
        st.markdown("**Vos hypothèses de marché**")

        market_direction = st.radio(
            "Direction anticipée",
            ["🚀 Forte hausse (+20% ou plus)", "📈 Légère hausse (+5% à +20%)",
             "➡️ Neutre (±5%)", "📉 Légère baisse (-5% à -20%)", "💥 Forte baisse (-20% ou plus)"],
            key="hyp_direction"
        )
        market_vol = st.radio(
            "Volatilité anticipée",
            ["🟢 Faible (marché calme)", "🟡 Modérée (normal)", "🔴 Élevée (marché agité)"],
            key="hyp_vol"
        )
        time_horizon = st.radio(
            "Horizon temporel",
            ["Court terme (< 1 semaine)", "Moyen terme (1-4 semaines)", "Long terme (> 1 mois)"],
            key="hyp_horizon"
        )
        conviction = st.slider("Niveau de conviction (%)", 10, 100, 60, key="hyp_conviction")

    with col_rec:
        st.markdown("**Recommandation du système**")

        # Logique de recommandation
        direction_score = {
            "🚀 Forte hausse (+20% ou plus)": 2,
            "📈 Légère hausse (+5% à +20%)": 1,
            "➡️ Neutre (±5%)": 0,
            "📉 Légère baisse (-5% à -20%)": -1,
            "💥 Forte baisse (-20% ou plus)": -2,
        }.get(market_direction, 0)

        vol_score = {
            "🟢 Faible (marché calme)": 0,
            "🟡 Modérée (normal)": 1,
            "🔴 Élevée (marché agité)": 2,
        }.get(market_vol, 1)

        horizon_score = {
            "Court terme (< 1 semaine)": 0,
            "Moyen terme (1-4 semaines)": 1,
            "Long terme (> 1 mois)": 2,
        }.get(time_horizon, 1)

        conviction_norm = conviction / 100

        # Recommandation
        if direction_score >= 1 and vol_score <= 1 and conviction_norm >= 0.6:
            best_strategy = "Momentum"
            guard_decision = "ALLOW"
            explanation = "Le marché est haussier avec une volatilité maîtrisée. La stratégie Momentum est optimale pour capturer la tendance."
            risk_level = "Faible à modéré"
            expected_pnl = f"+{direction_score * 8 * conviction_norm:.0f}% à +{direction_score * 15 * conviction_norm:.0f}%"
        elif direction_score <= -1 and vol_score <= 1:
            best_strategy = "Mean Reversion"
            guard_decision = "HOLD"
            explanation = "Le marché est baissier. La stratégie Mean Reversion peut capturer les rebonds, mais le Guard X-108 sera prudent."
            risk_level = "Modéré à élevé"
            expected_pnl = f"{direction_score * 5 * conviction_norm:.0f}% à {direction_score * 2 * conviction_norm:.0f}%"
        elif vol_score >= 2:
            best_strategy = "Hold ou DCA"
            guard_decision = "BLOCK"
            explanation = "La volatilité élevée rend toute stratégie risquée. Le Guard X-108 bloquerait la plupart des trades. Attendez un marché plus calme."
            risk_level = "Élevé"
            expected_pnl = "Imprévisible"
        elif direction_score == 0:
            best_strategy = "DCA"
            guard_decision = "HOLD"
            explanation = "Le marché est neutre. Le DCA (achat progressif) permet de lisser le prix d'entrée sans prendre de risque directionnel."
            risk_level = "Faible"
            expected_pnl = f"+{2 * conviction_norm:.0f}% à +{8 * conviction_norm:.0f}%"
        else:
            best_strategy = "Guard-Driven"
            guard_decision = "HOLD"
            explanation = "Les signaux sont mixtes. Laissez l'agent décider en temps réel avec le Guard X-108 comme filet de sécurité."
            risk_level = "Modéré"
            expected_pnl = f"-{5 * (1-conviction_norm):.0f}% à +{10 * conviction_norm:.0f}%"

        # Affichage
        guard_colors = {"ALLOW": "🟢", "HOLD": "🟡", "BLOCK": "🔴"}
        guard_bgs = {"ALLOW": "#0d2818", "HOLD": "#2d1f00", "BLOCK": "#2d0f0f"}
        guard_borders = {"ALLOW": "#2ea043", "HOLD": "#d29922", "BLOCK": "#f85149"}

        st.markdown(f"""
        <div style="background:{guard_bgs[guard_decision]}; border-left:4px solid {guard_borders[guard_decision]}; padding:16px; border-radius:8px; margin-bottom:12px;">
            <h3 style="color:{guard_borders[guard_decision]}; margin:0;">{guard_colors[guard_decision]} Guard X-108 : {guard_decision}</h3>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Stratégie recommandée : {best_strategy}**")
        st.info(explanation)

        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("Niveau de risque", risk_level)
        with col_r2:
            st.metric("PnL estimé", expected_pnl)
        with col_r3:
            st.metric("Conviction", f"{conviction}%")

        st.divider()
        st.markdown("**Paramètres Guard X-108 recommandés**")

        if vol_score >= 2:
            rec_threshold = 0.75
            rec_lock = 108
        elif vol_score == 1:
            rec_threshold = 0.60
            rec_lock = 54
        else:
            rec_threshold = 0.45
            rec_lock = 27

        st.markdown(f"- Seuil θ_S recommandé : **{rec_threshold}** (actuel : {st.session_state.get('guard_threshold', 0.55):.2f})")
        st.markdown(f"- Verrou temporel : **{rec_lock}s**")
        st.markdown(f"- Position size max : **{max(1, 5 - vol_score * 2)}%** du portefeuille")

        if st.button("Appliquer ces paramètres au Guard", use_container_width=True):
            st.session_state.guard_threshold = rec_threshold
            if "guard" in st.session_state:
                st.session_state.guard.threshold = rec_threshold
            st.success(f"✅ Seuil Guard mis à jour : θ_S = {rec_threshold}")
