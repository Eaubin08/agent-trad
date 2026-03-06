"""
Obsidia x ERC-8004 — EIP-712 Signer
Signe les TradeIntents selon le standard EIP-712 (Typed Structured Data Hashing).

En mode LIVE : utilise eth_account pour une vraie signature cryptographique.
En mode STUB : utilise SHA-256 pour la démo (pas de clé privée requise).
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict

try:
    from eth_account import Account
    from eth_account.messages import encode_structured_data
    ETH_ACCOUNT_AVAILABLE = True
except ImportError:
    ETH_ACCOUNT_AVAILABLE = False

from config.settings import AGENT_PRIVATE_KEY, BLOCKCHAIN_MODE


# ── Domaine EIP-712 du hackathon ─────────────────────────────────────────────
EIP712_DOMAIN = {
    "name": "ObsidiaTrading",
    "version": "1",
    "chainId": 11155111,  # Sepolia
    "verifyingContract": "0x0000000000000000000000000000000000000000",
}

TRADE_INTENT_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "TradeIntent": [
        {"name": "agentId", "type": "string"},
        {"name": "symbol", "type": "string"},
        {"name": "side", "type": "string"},
        {"name": "quantity", "type": "uint256"},
        {"name": "price", "type": "uint256"},
        {"name": "confidence", "type": "uint256"},
        {"name": "timestamp", "type": "uint256"},
        {"name": "artifactHash", "type": "bytes32"},
    ],
}


class EIP712Signer:
    def __init__(self, private_key: str = AGENT_PRIVATE_KEY or "demo-key") -> None:
        self.private_key = private_key
        self._use_live = (
            BLOCKCHAIN_MODE == "live"
            and ETH_ACCOUNT_AVAILABLE
            and private_key
            and private_key != "demo-key"
        )

    def sign_trade_intent(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        confidence: float,
        artifact_hash: str,
        agent_id: str = "obsidia-trustless-agent",
    ) -> Dict[str, Any]:
        """Signe un TradeIntent selon EIP-712."""
        ts = int(time.time())

        typed_data = {
            "agentId": agent_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "confidence": confidence,
            "timestamp": ts,
            "artifactHash": artifact_hash,
        }

        if self._use_live:
            return self._sign_live(typed_data, artifact_hash)

        return self._sign_stub(typed_data, artifact_hash)

    def _sign_live(self, typed_data: dict, artifact_hash: str) -> Dict[str, Any]:
        """Signature cryptographique réelle via eth_account."""
        try:
            structured = {
                "types": TRADE_INTENT_TYPES,
                "domain": EIP712_DOMAIN,
                "primaryType": "TradeIntent",
                "message": {
                    **typed_data,
                    "quantity": int(typed_data["quantity"] * 1e8),
                    "price": int(typed_data["price"] * 1e8),
                    "confidence": int(typed_data["confidence"] * 1e4),
                    "artifactHash": bytes.fromhex(artifact_hash[:64].ljust(64, "0")),
                },
            }
            encoded = encode_structured_data(structured)
            account = Account.from_key(self.private_key)
            signed = account.sign_message(encoded)
            return {
                "typed_data": typed_data,
                "signature": signed.signature.hex(),
                "signer": account.address,
                "scheme": "EIP-712",
                "mode": "live",
            }
        except Exception as e:
            return self._sign_stub(typed_data, artifact_hash, error=str(e))

    def _sign_stub(self, typed_data: dict, artifact_hash: str, error: str = "") -> Dict[str, Any]:
        """Signature SHA-256 pour la démo (sans clé privée)."""
        payload_str = json.dumps(typed_data, sort_keys=True) + self.private_key
        digest = hashlib.sha256(payload_str.encode()).hexdigest()
        result = {
            "typed_data": typed_data,
            "signature": f"0x{digest}",
            "scheme": "EIP-712-stub",
            "mode": "stub",
        }
        if error:
            result["fallback_reason"] = error
        return result
