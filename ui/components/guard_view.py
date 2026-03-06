"""
guard_view.py — Vue Guard X-108 : décision, score structurel S, verrou temporel.
"""
from __future__ import annotations

import streamlit as st
from core.guard_x108 import GuardResult, GuardDecision


DECISION_CONFIG = {
    GuardDecision.ALLOW: {"icon": "✅", "color": "#00d4aa", "label": "ALLOW"},
    GuardDecision.HOLD:  {"icon": "⏸️", "color": "#f5a623", "label": "HOLD"},
    GuardDecision.BLOCK: {"icon": "🚫", "color": "#ff4b6e", "label": "BLOCK"},
}


def render_guard_view(result: GuardResult) -> None:
    cfg = DECISION_CONFIG[result.decision]
    icon, color, label = cfg["icon"], cfg["color"], cfg["label"]

    st.subheader("🛡️ Guard X-108 — Décision souveraine")

    # Décision principale
    st.markdown(
        f"""
        <div style="
            background: rgba(0,0,0,0.3);
            border: 2px solid {color};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 16px;
        ">
            <div style="font-size: 3rem;">{icon}</div>
            <div style="font-size: 2rem; font-weight: bold; color: {color};">{label}</div>
            <div style="color: #aaa; margin-top: 8px;">{result.reason}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Métriques détaillées
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Score Structurel S",
        f"{result.structural_S:.4f}",
        help="S = α·T + β·H − γ·A (moteur Obsidia v18.3)"
    )
    c2.metric(
        "Seuil θ_S",
        f"{result.threshold_used:.2f}",
        help="Seuil ACT du moteur Obsidia"
    )
    c3.metric(
        "Verrou X-108",
        f"{result.temporal_lock_s:.0f}s",
        help="Délai minimum entre deux actions irréversibles"
    )

    # Artefact de validation
    with st.expander("🔍 Artefact de validation (Proof)"):
        artifact = result.validation_artifact
        col_a, col_b = st.columns(2)
        artifact_hash = artifact.get('artifact_hash', artifact.get('hash', '—'))
        col_a.markdown(f"**Hash :** `{artifact_hash[:20]}...`")
        col_b.markdown(f"**Timestamp :** `{artifact.get('timestamp', '—')}`")
        st.json({
            "decision": artifact.get("decision"),
            "risk_score": artifact.get("risk_score"),
            "structural_S": artifact.get("structural_S"),
            "consensus_side": artifact.get("consensus_side"),
            "consensus_confidence": artifact.get("consensus_confidence"),
        })
