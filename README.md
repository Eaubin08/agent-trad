# 🔮 Obsidia — Trustless Multi-Agent Trading System

> **AI Trading Agents ERC-8004 Hackathon** — Built for the "Best Compliance & Risk Guardrails" prize.

## What is this?

Obsidia is a **trustless, governed, multi-agent trading system** that makes every trading decision explainable, provable, and auditable before execution. It is fully compliant with the **ERC-8004 standard** (Trustless Agent Identity, Reputation, and Validation).

---

## Architecture

```
Market Data (Binance Live)
        │
        ▼
14 Deterministic Agents ──────────────────────────────────────────┐
  ├── Observation  : MarketData, Liquidity, Volatility, Macro      │
  ├── Technical    : Momentum, MeanReversion, Breakout, Pattern    │
  ├── Context      : Sentiment, Event, Correlation                 │
  └── Strategy     : Prediction, Portfolio, Aggregator            │
        │                                                          │
        ▼                                                          │
Weighted Consensus (confidence-weighted vote)                      │
        │                                                          │
        ▼                                                          │
Guard X-108 (Obsidia Structural Engine v18.3)                      │
  ├── Structural Score S = α·T + β·H - γ·A  (OS2 metrics)         │
  ├── X108 Temporal Lock (108s between irreversible actions)       │
  ├── Risk gates: volatility, drawdown, exposure, event risk       │
  └── Decision: ALLOW | HOLD | BLOCK                              │
        │                                                          │
        ▼                                                          │
ERC-8004 Hooks (Sepolia)                                           │
  ├── Validation Registry ← artifact_hash (SHA-256 proof)         │
  ├── EIP-712 Signature   ← TradeIntent signed                     │
  └── Risk Router         ← trustless execution                   │
        │                                                          │
        ▼                                                          │
Proof Logger (SHA-256 audit trail per cycle)                       │
```

---

## ERC-8004 Compliance

| Registry | Role | Status |
|---|---|---|
| **Identity Registry** | Agent identity on-chain | ✅ Implemented |
| **Validation Registry** | Pre-trade proof submission | ✅ Implemented |
| **Reputation Registry** | PnL & performance tracking | ✅ Implemented |
| **Risk Router** | Trustless trade execution | ✅ Implemented |

---

## Guard X-108 — Obsidia Structural Engine

The Guard X-108 uses the **Obsidia OS2 structural metrics** to evaluate agent cohesion before any trade:

- **T** (Triangle Closure Score): local coherence between agents
- **H** (Hexagon Density): meso-level connectivity
- **A** (Asymmetry Penalty): anti-domination guard
- **S = α·T + β·H - γ·A** ≥ 0.25 required to ALLOW a trade

This ensures no single agent can dominate the decision — the system requires **structural consensus**, not just a majority vote.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard (stub mode — no private key needed)
streamlit run ui/app.py

# 3. (Optional) Enable live blockchain mode
export BLOCKCHAIN_MODE=live
export SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
export AGENT_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
streamlit run ui/app.py
```

---

## Project Structure

```
agent-trad/
├── agents/
│   ├── indicators.py     # Technical + Obsidia structural indicators
│   └── registry.py       # 14 deterministic trading agents
├── blockchain/
│   ├── erc8004_client.py # ERC-8004 contracts client (Sepolia)
│   └── eip712_signer.py  # EIP-712 TradeIntent signer
├── config/
│   └── settings.py       # All configuration variables
├── core/
│   ├── guard_x108.py     # Guard X-108 (Obsidia OS2 engine)
│   ├── live_market.py    # Binance live market feed
│   ├── portfolio.py      # Portfolio & NAV management
│   └── logger.py         # SHA-256 proof logger
├── ui/
│   └── app.py            # Streamlit dashboard
├── logs/                 # Auto-generated proof logs
└── tests/                # Unit tests
```

---

## Built With

- **Python 3.11** — Core engine
- **Streamlit** — Dashboard
- **Binance API** — Live market data
- **web3.py + eth_account** — Blockchain interaction
- **Obsidia Engine v18.3** — Structural metrics (OS2)
- **ERC-8004** — Trustless agent standard

---

*Built for the AI Trading Agents ERC-8004 Hackathon on lablab.ai*
