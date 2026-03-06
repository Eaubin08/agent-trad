"""
agent_votes.py — Vue votes des 14 agents avec rationales et indicateurs.
"""
from __future__ import annotations

from typing import List

import streamlit as st
import plotly.graph_objects as go

from agents.registry import AgentVote

SIGNAL_COLOR = {
    "BUY":  "#00d4aa",
    "SELL": "#ff4b6e",
    "HOLD": "#f5a623",
}

CATEGORY_ICON = {
    "observation": "👁",
    "technique":   "📐",
    "contexte":    "🌍",
    "strategie":   "🧠",
    "meta":        "⚙️",
}


def render_agent_votes(votes: List[AgentVote], consensus: dict) -> None:
    st.subheader("🤖 14 Agents — Votes & Rationales")

    # Résumé consensus en haut
    side = consensus["side"]
    conf = consensus["confidence"]
    color = SIGNAL_COLOR.get(side, "#888")

    c1, c2, c3 = st.columns(3)
    c1.metric("Consensus", side, help="Signal majoritaire pondéré par la confiance")
    c2.metric("Confiance", f"{conf:.0%}")
    c3.metric("Agents actifs", str(len(votes)))

    # Barre de répartition BUY/SELL/HOLD
    total = consensus["buy_weight"] + consensus["sell_weight"] + consensus["hold_weight"]
    if total > 0:
        fig = go.Figure()
        for label, key, color_bar in [
            ("BUY",  "buy_weight",  "#00d4aa"),
            ("HOLD", "hold_weight", "#f5a623"),
            ("SELL", "sell_weight", "#ff4b6e"),
        ]:
            fig.add_trace(go.Bar(
                name=label,
                x=[consensus[key] / total],
                orientation="h",
                marker_color=color_bar,
                text=f"{consensus[key]/total:.0%}",
                textposition="inside",
            ))
        fig.update_layout(
            barmode="stack",
            height=50,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 1]),
            yaxis=dict(showgrid=False, showticklabels=False),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Grouper par catégorie
    categories: dict[str, List[AgentVote]] = {}
    for v in votes:
        categories.setdefault(v.category, []).append(v)

    for cat, cat_votes in categories.items():
        icon = CATEGORY_ICON.get(cat, "•")
        with st.expander(f"{icon} **{cat.upper()}** — {len(cat_votes)} agents", expanded=True):
            for v in cat_votes:
                sig_color = SIGNAL_COLOR.get(v.signal, "#888")
                col_name, col_sig, col_conf, col_rat = st.columns([2.5, 1, 1, 4])
                col_name.markdown(f"**{v.name}**")
                col_sig.markdown(
                    f"<span style='color:{sig_color};font-weight:bold'>{v.signal}</span>",
                    unsafe_allow_html=True
                )
                col_conf.markdown(f"`{v.confidence:.0%}`")
                col_rat.caption(v.rationale)
