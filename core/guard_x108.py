"""
Obsidia x ERC-8004 — Guard X-108
Couche souveraine de gouvernance pré-trade.

Intègre les métriques structurelles du moteur Obsidia (OS2) :
- Score S = alpha*T + beta*H - gamma*A
  T = cohésion triangulaire entre agents
  H = densité de connexion (proxy meso)
  A = pénalité d'asymétrie (anti-domination)
- Seuil ACT : S >= 0.25 (theta_S du moteur Obsidia v18.3)
- X108Gate : verrou temporel sur les actions irréversibles (min_wait_s=108s)

Décisions : ALLOW | HOLD | BLOCK
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.indicators import structural_score
from agents.registry import AgentVote


class GuardDecision(str, Enum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


@dataclass
class GuardResult:
    decision: GuardDecision
    reason: str
    risk_score: float
    structural_S: float
    threshold_used: float
    temporal_lock_s: float
    validation_artifact: Dict[str, Any]


def _build_coherence_matrix(votes: List[AgentVote]) -> List[List[float]]:
    """
    Construit la matrice de cohésion W entre agents.
    W[i][j] = 1.0 si les agents i et j votent dans le même sens, 0.0 sinon.
    Utilisé pour calculer le score structurel S du moteur Obsidia.
    """
    n = len(votes)
    W = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                W[i][j] = 1.0
            elif votes[i].signal == votes[j].signal:
                # Cohésion pondérée par la confiance moyenne
                W[i][j] = (votes[i].confidence + votes[j].confidence) / 2.0
    return W


class GuardX108:
    """
    Guard X-108 — Couche souveraine Obsidia.

    Paramètres :
    - base_threshold : seuil de confiance minimum pour ALLOW (0.18)
    - min_consensus : ratio minimum de votes concordants (0.70)
    - theta_S : seuil du score structurel Obsidia pour valider la cohésion (0.25)
    - min_wait_s : verrou temporel X108 entre deux trades irréversibles (108s)
    """

    def __init__(
        self,
        base_threshold: float = 0.18,
        min_consensus: float = 0.70,
        theta_S: float = 0.25,
        min_wait_s: float = 108.0,
    ) -> None:
        self.base_threshold = base_threshold
        self.min_consensus = min_consensus
        self.theta_S = theta_S
        self.min_wait_s = min_wait_s
        self._last_allow_ts: float = 0.0

    def evaluate(
        self,
        votes: List[AgentVote],
        consensus: dict,
        snapshot_volatility: float,
        snapshot_event_risk: float,
        exposure: float,
        drawdown: float,
        prediction_risk: float,
    ) -> GuardResult:
        side = consensus["side"]
        confidence = consensus["confidence"]
        elapsed = time.time() - self._last_allow_ts

        # ── Score structurel Obsidia (OS2) ──────────────────────────────
        active_votes = [v for v in votes if v.name != "SignalAggregatorAgent"]
        W = _build_coherence_matrix(active_votes)
        S = structural_score(W)

        # ── Calcul du risk_score composite ──────────────────────────────
        risk_score = max(snapshot_volatility, snapshot_event_risk, prediction_risk, exposure)

        # ── Règles de décision (ordre de priorité) ───────────────────────

        # 1. Risque événementiel critique → BLOCK immédiat
        if snapshot_event_risk > 0.88:
            decision = GuardDecision.BLOCK
            reason = f"Event risk critical ({snapshot_event_risk:.2f} > 0.88)"

        # 2. Drawdown excessif → BLOCK
        elif drawdown > 0.15:
            decision = GuardDecision.BLOCK
            reason = f"Drawdown too high ({drawdown:.2%})"

        # 3. Exposition maximale sur BUY → BLOCK
        elif exposure > 0.85 and side == "BUY":
            decision = GuardDecision.BLOCK
            reason = f"Exposure cap reached ({exposure:.2%})"

        # 4. Score structurel Obsidia insuffisant → HOLD
        elif S < self.theta_S:
            decision = GuardDecision.HOLD
            reason = f"Structural score S={S:.3f} < theta_S={self.theta_S} (low agent cohesion)"

        # 5. Confiance ou consensus insuffisant → HOLD
        elif confidence < self.base_threshold or consensus["confidence"] < self.min_consensus:
            decision = GuardDecision.HOLD
            reason = f"Consensus/confidence below threshold (conf={confidence:.2f})"

        # 6. Volatilité trop élevée → HOLD
        elif snapshot_volatility > 0.58:
            decision = GuardDecision.HOLD
            reason = f"Volatility too high ({snapshot_volatility:.2f} > 0.58)"

        # 7. Verrou temporel X108 (irréversible) → HOLD
        elif side in ("BUY", "SELL") and elapsed < self.min_wait_s:
            wait = self.min_wait_s - elapsed
            decision = GuardDecision.HOLD
            reason = f"X108 temporal lock: wait +{wait:.0f}s (elapsed={elapsed:.0f}s)"

        # 8. Tous les checks passés → ALLOW
        else:
            decision = GuardDecision.ALLOW
            reason = "All risk checks passed (structural + temporal + market)"
            self._last_allow_ts = time.time()

        # ── Construction de l'artefact de validation ─────────────────────
        artifact_core = {
            "symbol": votes[0].name if votes else "UNKNOWN",
            "side": side,
            "decision": decision.value,
            "reason": reason,
            "confidence": confidence,
            "structural_S": round(S, 4),
            "theta_S": self.theta_S,
            "risk_score": round(risk_score, 4),
            "snapshot_volatility": round(snapshot_volatility, 4),
            "snapshot_event_risk": round(snapshot_event_risk, 4),
            "prediction_risk": round(prediction_risk, 4),
            "exposure": round(exposure, 4),
            "drawdown": round(drawdown, 4),
            "x108_elapsed_s": round(elapsed, 1),
            "x108_min_wait_s": self.min_wait_s,
            "timestamp": int(time.time()),
        }
        artifact_hash = hashlib.sha256(
            json.dumps(artifact_core, sort_keys=True).encode()
        ).hexdigest()
        artifact_core["artifact_hash"] = artifact_hash

        return GuardResult(
            decision=decision,
            reason=reason,
            risk_score=risk_score,
            structural_S=S,
            threshold_used=self.base_threshold,
            temporal_lock_s=self.min_wait_s,
            validation_artifact=artifact_core,
        )
