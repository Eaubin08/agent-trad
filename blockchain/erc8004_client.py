"""
Obsidia x ERC-8004 — ERC-8004 Client
Interagit avec les contrats ERC-8004 déployés sur Sepolia.

Contrats (réseau Sepolia - hackathon AI Trading Agents ERC-8004) :
- Identity Registry  : 0xf66e4B5e1f5E8F5e1f5E8F5e1f5E8F5e1f5E8F5e (stub)
- Validation Registry: 0xC261...  (stub)
- Reputation Registry: 0x6E2a...  (stub)
- Risk Router        : 0xRisk...  (stub)

En mode LIVE : utilise web3.py avec RPC Sepolia (Infura/Alchemy).
En mode STUB : simule les appels pour la démo (pas de clé privée requise).

Pour activer le mode LIVE :
1. Définir SEPOLIA_RPC_URL dans config/settings.py
2. Définir AGENT_PRIVATE_KEY dans config/settings.py
3. Mettre BLOCKCHAIN_MODE = "live" dans config/settings.py
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from web3 import Web3
    from eth_account import Account
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

from config.settings import (
    BLOCKCHAIN_MODE,
    SEPOLIA_RPC_URL,
    AGENT_PRIVATE_KEY,
    IDENTITY_REGISTRY_ADDRESS,
    VALIDATION_REGISTRY_ADDRESS,
    REPUTATION_REGISTRY_ADDRESS,
    RISK_ROUTER_ADDRESS,
)


@dataclass
class ERC8004Config:
    identity_registry: str = IDENTITY_REGISTRY_ADDRESS
    validation_registry: str = VALIDATION_REGISTRY_ADDRESS
    reputation_registry: str = REPUTATION_REGISTRY_ADDRESS
    risk_router: str = RISK_ROUTER_ADDRESS
    chain: str = "Sepolia"
    mode: str = BLOCKCHAIN_MODE


class ERC8004Client:
    """
    Client ERC-8004 avec support mode LIVE (Sepolia) et STUB (démo).
    """

    def __init__(self, config: Optional[ERC8004Config] = None) -> None:
        self.config = config or ERC8004Config()
        self.agent_id: Optional[str] = None
        self._w3: Optional[Any] = None
        self._account: Optional[Any] = None

        if self.config.mode == "live" and WEB3_AVAILABLE and SEPOLIA_RPC_URL:
            try:
                self._w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
                if AGENT_PRIVATE_KEY:
                    self._account = Account.from_key(AGENT_PRIVATE_KEY)
            except Exception as e:
                print(f"[ERC8004] Web3 init failed, falling back to stub: {e}")

    def _is_live(self) -> bool:
        return (
            self.config.mode == "live"
            and self._w3 is not None
            and self._w3.is_connected()
        )

    # ── Identity Registry ────────────────────────────────────────────────

    def register_identity(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Enregistre l'agent sur l'Identity Registry ERC-8004."""
        agent_id = profile.get("name", "obsidia-agent").lower().replace(" ", "-")
        self.agent_id = agent_id

        if self._is_live():
            return self._register_identity_live(profile, agent_id)

        # Mode STUB
        return {
            "status": "registered",
            "agent_id": agent_id,
            "identity_registry": self.config.identity_registry,
            "chain": self.config.chain,
            "mode": "stub",
            "tx_hash": "0x" + hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()[:40],
            "timestamp": int(time.time()),
        }

    def _register_identity_live(self, profile: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """Appel réel au contrat Identity Registry sur Sepolia."""
        try:
            # ABI minimal ERC-8004 Identity Registry
            abi = [
                {
                    "inputs": [
                        {"name": "agentId", "type": "string"},
                        {"name": "metadataUri", "type": "string"},
                    ],
                    "name": "register",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ]
            contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.config.identity_registry),
                abi=abi,
            )
            metadata_uri = f"ipfs://obsidia/{agent_id}"
            tx = contract.functions.register(agent_id, metadata_uri).build_transaction(
                {
                    "from": self._account.address,
                    "nonce": self._w3.eth.get_transaction_count(self._account.address),
                    "gas": 200_000,
                    "gasPrice": self._w3.eth.gas_price,
                }
            )
            signed = self._account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return {
                "status": "registered",
                "agent_id": agent_id,
                "identity_registry": self.config.identity_registry,
                "chain": self.config.chain,
                "mode": "live",
                "tx_hash": tx_hash.hex(),
                "block": receipt.blockNumber,
            }
        except Exception as e:
            return {
                "status": "error",
                "agent_id": agent_id,
                "error": str(e),
                "mode": "live_failed",
            }

    # ── Validation Registry ──────────────────────────────────────────────

    def submit_validation(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Soumet l'artefact de validation pré-trade au Validation Registry."""
        artifact_hash = artifact.get("artifact_hash", "")

        if self._is_live():
            return self._submit_validation_live(artifact_hash)

        return {
            "status": "validated",
            "validation_registry": self.config.validation_registry,
            "artifact_hash": artifact_hash,
            "chain": self.config.chain,
            "mode": "stub",
            "timestamp": int(time.time()),
        }

    def _submit_validation_live(self, artifact_hash: str) -> Dict[str, Any]:
        try:
            abi = [
                {
                    "inputs": [
                        {"name": "agentId", "type": "string"},
                        {"name": "artifactHash", "type": "bytes32"},
                    ],
                    "name": "submitValidation",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ]
            contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.config.validation_registry),
                abi=abi,
            )
            hash_bytes = bytes.fromhex(artifact_hash[:64].ljust(64, "0"))
            tx = contract.functions.submitValidation(
                self.agent_id or "obsidia", hash_bytes
            ).build_transaction(
                {
                    "from": self._account.address,
                    "nonce": self._w3.eth.get_transaction_count(self._account.address),
                    "gas": 150_000,
                    "gasPrice": self._w3.eth.gas_price,
                }
            )
            signed = self._account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return {
                "status": "validated",
                "validation_registry": self.config.validation_registry,
                "artifact_hash": artifact_hash,
                "mode": "live",
                "tx_hash": tx_hash.hex(),
                "block": receipt.blockNumber,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "mode": "live_failed"}

    # ── Risk Router ──────────────────────────────────────────────────────

    def route_trade_intent(self, signed_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Envoie le TradeIntent signé au Risk Router du hackathon."""
        if self._is_live():
            return self._route_live(signed_intent)

        return {
            "status": "routed",
            "risk_router": self.config.risk_router,
            "trade_hash": signed_intent.get("signature", "")[:20] + "...",
            "chain": self.config.chain,
            "mode": "stub",
            "timestamp": int(time.time()),
        }

    def _route_live(self, signed_intent: Dict[str, Any]) -> Dict[str, Any]:
        try:
            abi = [
                {
                    "inputs": [
                        {"name": "agentId", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "side", "type": "string"},
                        {"name": "quantity", "type": "uint256"},
                        {"name": "signature", "type": "bytes"},
                    ],
                    "name": "routeIntent",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ]
            contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.config.risk_router),
                abi=abi,
            )
            typed_data = signed_intent.get("typed_data", {})
            sig_hex = signed_intent.get("signature", "0x")
            sig_bytes = bytes.fromhex(sig_hex[2:]) if sig_hex.startswith("0x") else b""
            qty_wei = int(float(typed_data.get("quantity", 0)) * 1e8)

            tx = contract.functions.routeIntent(
                self.agent_id or "obsidia",
                typed_data.get("symbol", "BTC/USDT"),
                typed_data.get("side", "HOLD"),
                qty_wei,
                sig_bytes,
            ).build_transaction(
                {
                    "from": self._account.address,
                    "nonce": self._w3.eth.get_transaction_count(self._account.address),
                    "gas": 200_000,
                    "gasPrice": self._w3.eth.gas_price,
                }
            )
            signed = self._account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return {
                "status": "routed",
                "risk_router": self.config.risk_router,
                "mode": "live",
                "tx_hash": tx_hash.hex(),
                "block": receipt.blockNumber,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "mode": "live_failed"}

    # ── Reputation Registry ──────────────────────────────────────────────

    def update_reputation(self, pnl: float, trade_count: int) -> Dict[str, Any]:
        """Met à jour le Reputation Registry après chaque cycle."""
        return {
            "status": "updated",
            "reputation_registry": self.config.reputation_registry,
            "agent_id": self.agent_id,
            "pnl": round(pnl, 4),
            "trade_count": trade_count,
            "mode": "stub",
            "timestamp": int(time.time()),
        }
