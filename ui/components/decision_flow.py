"""
decision_flow.py — Vue Decision Flow : pipeline complet Market → Risk Router.
"""
from __future__ import annotations

import streamlit as st
from core.guard_x108 import GuardResult, GuardDecision

STEP_COLORS = {
    "active":   "#00d4aa",
    "pending":  "#444",
    "blocked":  "#ff4b6e",
}


def render_decision_flow(guard_result: GuardResult, consensus: dict) -> None:
    st.subheader("🔄 Decision Flow — Pipeline ERC-8004")

    decision = guard_result.decision
    is_allow = decision == GuardDecision.ALLOW
    is_block = decision == GuardDecision.BLOCK

    steps = [
        {
            "label": "Market Feed",
            "icon": "📡",
            "detail": "Binance WebSocket — BTC/USDT live",
            "status": "active",
        },
        {
            "label": "14 Agents",
            "icon": "🤖",
            "detail": f"Consensus: {consensus['side']} @ {consensus['confidence']:.0%}",
            "status": "active",
        },
        {
            "label": "Signal Aggregation",
            "icon": "⚡",
            "detail": f"BUY {consensus['buy_weight']:.2f} | SELL {consensus['sell_weight']:.2f} | HOLD {consensus['hold_weight']:.2f}",
            "status": "active",
        },
        {
            "label": "Guard X-108",
            "icon": "🛡️",
            "detail": f"S={guard_result.structural_S:.4f} → {decision.value}",
            "status": "active" if not is_block else "blocked",
        },
        {
            "label": "TradeIntent",
            "icon": "📝",
            "detail": "Création de l'intention de trade signée EIP-712",
            "status": "active" if is_allow else "pending",
        },
        {
            "label": "ERC-8004 Validation",
            "icon": "🔐",
            "detail": "Validation Registry — preuve on-chain",
            "status": "active" if is_allow else "pending",
        },
        {
            "label": "Risk Router",
            "icon": "🏦",
            "detail": "Exécution sur Sepolia Testnet",
            "status": "active" if is_allow else "pending",
        },
    ]

    # Rendu visuel du pipeline
    html_steps = ""
    for i, step in enumerate(steps):
        color = STEP_COLORS[step["status"]]
        connector = "" if i == len(steps) - 1 else f"""
            <div style="
                width: 2px;
                height: 24px;
                background: {color};
                margin: 0 auto;
                opacity: 0.5;
            "></div>
        """
        html_steps += f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 10px 16px;
            border-left: 3px solid {color};
            margin-bottom: 4px;
            background: rgba(255,255,255,0.02);
            border-radius: 0 8px 8px 0;
        ">
            <span style="font-size: 1.4rem;">{step['icon']}</span>
            <div>
                <div style="font-weight: bold; color: {color};">{step['label']}</div>
                <div style="font-size: 0.8rem; color: #888;">{step['detail']}</div>
            </div>
            <div style="margin-left: auto; font-size: 0.75rem; color: {color};">
                {'● LIVE' if step['status'] == 'active' else ('✗ BLOCKED' if step['status'] == 'blocked' else '○ PENDING')}
            </div>
        </div>
        {connector}
        """

    st.markdown(
        f'<div style="max-width: 600px; margin: 0 auto;">{html_steps}</div>',
        unsafe_allow_html=True
    )
