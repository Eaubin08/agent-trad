"""
Obsidia x ERC-8004 — Configuration
Variables de configuration du projet hackathon.

Pour activer le mode LIVE :
1. Mettre BLOCKCHAIN_MODE = "live"
2. Renseigner SEPOLIA_RPC_URL (ex: https://sepolia.infura.io/v3/YOUR_KEY)
3. Renseigner AGENT_PRIVATE_KEY (clé privée du wallet de test)
"""
import os

# ── Mode blockchain ──────────────────────────────────────────────────────────
# "stub" = simulation (démo, pas de clé privée requise)
# "live" = vrais appels sur Sepolia (nécessite RPC + clé privée)
BLOCKCHAIN_MODE: str = os.getenv("BLOCKCHAIN_MODE", "stub")

# ── Connexion Sepolia ────────────────────────────────────────────────────────
SEPOLIA_RPC_URL: str = os.getenv("SEPOLIA_RPC_URL", "")
AGENT_PRIVATE_KEY: str = os.getenv("AGENT_PRIVATE_KEY", "")

# ── Adresses des contrats ERC-8004 sur Sepolia ───────────────────────────────
# Source : hackathon AI Trading Agents ERC-8004 (lablab.ai)
# Remplacer par les adresses officielles communiquées par les organisateurs
IDENTITY_REGISTRY_ADDRESS: str = os.getenv(
    "IDENTITY_REGISTRY_ADDRESS", "0xf66e4B5e1f5E8F5e1f5E8F5e1f5E8F5e1f5E8F5e"
)
VALIDATION_REGISTRY_ADDRESS: str = os.getenv(
    "VALIDATION_REGISTRY_ADDRESS", "0xC261a4B5e1f5E8F5e1f5E8F5e1f5E8F5e1f5E8F5"
)
REPUTATION_REGISTRY_ADDRESS: str = os.getenv(
    "REPUTATION_REGISTRY_ADDRESS", "0x6E2a4B5e1f5E8F5e1f5E8F5e1f5E8F5e1f5E8F5e"
)
RISK_ROUTER_ADDRESS: str = os.getenv(
    "RISK_ROUTER_ADDRESS", "0xRisk4B5e1f5E8F5e1f5E8F5e1f5E8F5e1f5E8F5e"
)

# ── Profil de l'agent ────────────────────────────────────────────────────────
AGENT_PROFILE = {
    "name": "Obsidia Trustless Trading Agent",
    "description": (
        "14-agent governed trading system powered by Guard X-108. "
        "Every trade decision is validated, explainable, and provable before execution. "
        "Built for the AI Trading Agents ERC-8004 Hackathon."
    ),
    "wallet": os.getenv("AGENT_WALLET", "0xDEMO000000000000000000000000000000000001"),
    "network": "Sepolia",
    "capabilities": ["trade", "manage-risk", "protect-capital", "optimize-portfolio"],
    "version": "2.0.0",
    "engine": "Obsidia v18.3 + ERC-8004",
}

# ── Aliases pratiques pour les pages UI ─────────────────────────────────────
AGENT_NAME: str = AGENT_PROFILE["name"]
AGENT_VERSION: str = AGENT_PROFILE["version"]
AGENT_DESCRIPTION: str = AGENT_PROFILE["description"]

# ── Paramètres de trading ────────────────────────────────────────────────────
TRADING_SYMBOL: str = os.getenv("TRADING_SYMBOL", "BTCUSDT")
POSITION_SIZE_PCT: float = float(os.getenv("POSITION_SIZE_PCT", "0.03"))  # 3% du NAV par trade
INITIAL_CAPITAL: float = float(os.getenv("INITIAL_CAPITAL", "10000.0"))   # Capital de test hackathon

# ── Paramètres du Guard X-108 ────────────────────────────────────────────────
GUARD_BASE_THRESHOLD: float = float(os.getenv("GUARD_BASE_THRESHOLD", "0.18"))
GUARD_MIN_CONSENSUS: float = float(os.getenv("GUARD_MIN_CONSENSUS", "0.55"))
GUARD_THETA_S: float = float(os.getenv("GUARD_THETA_S", "0.25"))  # Seuil structurel Obsidia OS2
GUARD_MIN_WAIT_S: float = float(os.getenv("GUARD_MIN_WAIT_S", "108.0"))  # Verrou X108
