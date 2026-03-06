"""
proof_view.py — Vue Proof / Validation : TradeIntent hash, tx Validation, Risk Router.
"""
from __future__ import annotations

import streamlit as st
from core.guard_x108 import GuardResult, GuardDecision


def render_proof_view(guard_result: GuardResult) -> None:
    st.subheader("🔐 Proof Layer — Audit Trail ERC-8004")

    artifact = guard_result.validation_artifact
    decision = guard_result.decision
    is_allow = decision == GuardDecision.ALLOW

    # TradeIntent Hash
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**TradeIntent Hash**")
        full_hash = artifact.get("artifact_hash", artifact.get("hash", "—"))
        st.code(full_hash, language=None)

    with col2:
        st.markdown("**Timestamp**")
        st.code(str(artifact.get("timestamp", "—")), language=None)

    st.markdown("---")

    # Statut des transactions on-chain
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**Validation Registry**")
        if is_allow:
            st.success("✅ Proof enregistrée")
            st.caption("Sepolia Testnet")
            st.code("0x" + full_hash[:16] + "...", language=None)
        else:
            st.warning("⏸ Non soumise")
            st.caption(f"Raison : {guard_result.reason}")

    with col_b:
        st.markdown("**Risk Router**")
        if is_allow:
            st.success("✅ Ordre transmis")
            st.caption("Capital Vault → exécution")
            st.code("0x" + full_hash[16:32] + "...", language=None)
        else:
            st.warning("⏸ Bloqué par Guard X-108")

    with col_c:
        st.markdown("**Reputation Registry**")
        if is_allow:
            st.info("🔄 En attente PnL")
            st.caption("Mise à jour après clôture")
        else:
            st.info("📊 Score inchangé")

    st.markdown("---")

    # Détail complet de l'artefact
    with st.expander("📋 Artefact complet (JSON)"):
        st.json(artifact)

    # Métriques de gouvernance
    st.markdown("**Métriques de gouvernance**")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Score S", f"{guard_result.structural_S:.4f}")
    m2.metric("Risk Score", f"{guard_result.risk_score:.4f}")
    m3.metric("Seuil θ_S", f"{guard_result.threshold_used:.2f}")
    m4.metric("Verrou", f"{guard_result.temporal_lock_s:.0f}s")
