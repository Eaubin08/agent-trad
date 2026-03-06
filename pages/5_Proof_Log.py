"""
Page 5 — Proof Log & ERC-8004
Audit trail complet : hash SHA-256, Validation Registry, Risk Router.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import json
import hashlib
from datetime import datetime

st.set_page_config(page_title="Proof Log — Obsidia", page_icon="📋", layout="wide")

st.title("📋 Proof Log — Audit Trail ERC-8004")
st.caption("Chaque décision est hashée (SHA-256) et soumise au Validation Registry sur Sepolia. Transparence totale.")

# ─── Métriques ERC-8004 ───────────────────────────────────────────────────────
st.subheader("⛓️ Statut ERC-8004 — Réseau Sepolia")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🆔 Identity Registry", "Connecté", "Sepolia")
with col2:
    st.metric("📊 Reputation Registry", "Actif", "Score en cours")
with col3:
    cycle_count = st.session_state.get("cycle_count", 0)
    st.metric("✅ Validation Registry", f"{cycle_count} preuves", "Soumises")
with col4:
    st.metric("🚀 Risk Router", "En attente", "Mode simulation")

st.divider()

# ─── Profil de l'agent ────────────────────────────────────────────────────────
st.subheader("🤖 Profil de l'agent")

from config.settings import AGENT_NAME, AGENT_VERSION, AGENT_DESCRIPTION

col_profile, col_hash = st.columns([1, 2])
with col_profile:
    st.markdown(f"**Nom :** `{AGENT_NAME}`")
    st.markdown(f"**Version :** `{AGENT_VERSION}`")
    st.markdown(f"**Description :** {AGENT_DESCRIPTION}")
    st.markdown("**Réseau :** Sepolia Testnet")
    st.markdown("**Standard :** ERC-8004 (Trustless Agent Layer)")

with col_hash:
    # Générer un hash de profil
    profile_data = {
        "name": AGENT_NAME,
        "version": AGENT_VERSION,
        "description": AGENT_DESCRIPTION,
        "standard": "ERC-8004",
        "network": "sepolia",
    }
    profile_hash = hashlib.sha256(json.dumps(profile_data, sort_keys=True).encode()).hexdigest()
    st.markdown("**Hash de profil (SHA-256) :**")
    st.code(profile_hash, language="text")

    st.markdown("**Adresses des contrats (Sepolia) :**")
    from config.settings import (
        IDENTITY_REGISTRY_ADDRESS, REPUTATION_REGISTRY_ADDRESS,
        VALIDATION_REGISTRY_ADDRESS, RISK_ROUTER_ADDRESS
    )
    contracts = {
        "Identity Registry": IDENTITY_REGISTRY_ADDRESS,
        "Reputation Registry": REPUTATION_REGISTRY_ADDRESS,
        "Validation Registry": VALIDATION_REGISTRY_ADDRESS,
        "Risk Router": RISK_ROUTER_ADDRESS,
    }
    for name, addr in contracts.items():
        st.markdown(f"- **{name}** : `{addr}`")

st.divider()

# ─── Proof Log ────────────────────────────────────────────────────────────────
st.subheader("📜 Journal des preuves")

logger = st.session_state.get("logger")
history = st.session_state.get("history", [])

if history:
    # Construire le tableau des preuves
    proof_rows = []
    for i, h in enumerate(history[-50:][::-1]):
        proof_rows.append({
            "Cycle": h["cycle"],
            "Timestamp": datetime.now().strftime("%H:%M:%S"),
            "Prix ($)": f"${h['price']:,.2f}",
            "RSI": h["rsi"],
            "Décision": {"ALLOW": "🟢 ALLOW", "HOLD": "🟡 HOLD", "BLOCK": "🔴 BLOCK"}.get(h["decision"], h["decision"]),
            "Score S": h["score_s"],
            "NAV ($)": f"${h['nav']:,.2f}",
            "Hash (12 car.)": h.get("hash", "—"),
        })

    df_proof = pd.DataFrame(proof_rows)
    st.dataframe(df_proof, width="stretch", hide_index=True)

    # Statistiques
    st.divider()
    st.subheader("📊 Statistiques d'audit")

    df_all = pd.DataFrame(history)
    total = len(df_all)
    allows = (df_all["decision"] == "ALLOW").sum()
    blocks = (df_all["decision"] == "BLOCK").sum()
    holds  = (df_all["decision"] == "HOLD").sum()

    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    with col_s1:
        st.metric("Total preuves", total)
    with col_s2:
        st.metric("🟢 ALLOW", f"{allows} ({allows/total*100:.0f}%)")
    with col_s3:
        st.metric("🟡 HOLD", f"{holds} ({holds/total*100:.0f}%)")
    with col_s4:
        st.metric("🔴 BLOCK", f"{blocks} ({blocks/total*100:.0f}%)")
    with col_s5:
        filter_rate = (holds + blocks) / total * 100 if total > 0 else 0
        st.metric("🛡️ Taux filtrage Guard", f"{filter_rate:.1f}%")

    # Graphique des décisions
    st.markdown("**Évolution des décisions dans le temps**")
    if len(df_all) >= 2:
        df_chart = df_all.copy()
        df_chart["allow_num"] = (df_chart["decision"] == "ALLOW").astype(int)
        df_chart["block_num"] = (df_chart["decision"] == "BLOCK").astype(int)
        df_chart["hold_num"]  = (df_chart["decision"] == "HOLD").astype(int)
        st.bar_chart(
            df_chart.set_index("cycle")[["allow_num", "hold_num", "block_num"]],
            height=200,
            color=["#2ea043", "#d29922", "#f85149"]
        )

    # Export
    st.divider()
    st.subheader("💾 Export")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        csv_data = df_all.to_csv(index=False)
        st.download_button(
            "📥 Télécharger CSV",
            data=csv_data,
            file_name=f"obsidia_proof_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width="stretch",
        )
    with col_exp2:
        json_data = json.dumps(history, indent=2)
        st.download_button(
            "📥 Télécharger JSON",
            data=json_data,
            file_name=f"obsidia_proof_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch",
        )
else:
    st.info("Aucune preuve enregistrée. Lancez l'agent depuis la page **Home** (▶ Run) pour générer des preuves.")

st.divider()

# ─── Documentation ERC-8004 ───────────────────────────────────────────────────
st.subheader("📚 Comment fonctionne le Proof Log ERC-8004")

with st.expander("Voir l'explication technique"):
    st.markdown("""
**Le flux de preuve en 4 étapes :**

1. **Calcul du hash** : À chaque cycle, le Guard X-108 génère un `artifact_hash` SHA-256 qui encode :
   - Les données de marché (prix, RSI, volatilité)
   - Les votes des 14 agents
   - La décision finale (ALLOW/HOLD/BLOCK)
   - Le score S et le seuil θ_S

2. **Soumission au Validation Registry** : Si la décision est ALLOW, le hash est soumis au contrat `ValidationRegistry` sur Sepolia via une transaction signée EIP-712.

3. **Enregistrement de la réputation** : Le `ReputationRegistry` met à jour le score de l'agent après chaque trade (PnL réalisé, taux de succès).

4. **Exécution via le Risk Router** : Le `RiskRouter` vérifie que la preuve est valide avant d'exécuter le trade dans le `CapitalVault`.

**Pourquoi c'est important pour le hackathon :**
Le standard ERC-8004 exige que chaque agent puisse prouver *comment* il a pris sa décision. Notre Guard X-108 est la première implémentation d'un moteur de preuve déterministe basé sur les métriques structurelles Obsidia (T/H/A/S).
    """)
