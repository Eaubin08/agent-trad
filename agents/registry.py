"""
Obsidia x ERC-8004 — 14 Agents Déterministes
Chaque agent produit un vote BUY/SELL/HOLD justifiable financièrement.
Source : patch obsidia_agents_intelligent + logique Obsidia-lab-trad.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional

from agents.indicators import (
    MarketState,
    atr,
    bollinger,
    ema,
    macd,
    realized_volatility,
    rsi,
    sma,
    zscore,
)

Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class AgentVote:
    name: str
    signal: Signal
    confidence: float
    rationale: str
    category: str


class BaseAgent:
    name: str = "BaseAgent"
    category: str = "generic"

    def vote(self, state: MarketState) -> AgentVote:
        raise NotImplementedError

    @staticmethod
    def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, x))


# ─── FAMILLE OBSERVATION ───────────────────────────────────────────────────

class MarketDataAgent(BaseAgent):
    name = "MarketDataAgent"
    category = "observation"

    def vote(self, state: MarketState) -> AgentVote:
        if len(state.prices) < 2:
            return AgentVote(self.name, "HOLD", 0.2, "insufficient data", self.category)
        last, prev = state.prices[-1], state.prices[-2]
        change = (last - prev) / prev if prev else 0.0
        signal: Signal = "BUY" if change > 0.001 else "SELL" if change < -0.001 else "HOLD"
        conf = self._clamp(abs(change) * 25)
        return AgentVote(self.name, signal, conf, f"1-step change={change:.4f}", self.category)


class LiquidityAgent(BaseAgent):
    name = "LiquidityAgent"
    category = "observation"

    def vote(self, state: MarketState) -> AgentVote:
        if len(state.volumes) < 20:
            return AgentVote(self.name, "HOLD", 0.2, "insufficient volume history", self.category)
        current_vol = state.volumes[-1]
        avg_vol = sum(list(state.volumes)[-20:]) / 20
        current_spread = state.spreads_bps[-1]
        avg_spread = sum(list(state.spreads_bps)[-20:]) / 20
        tight = current_spread < max(10.0, avg_spread)
        if current_vol > avg_vol and tight:
            signal: Signal = "BUY"
        elif current_vol < 0.6 * avg_vol or current_spread > 20:
            signal = "SELL"
        else:
            signal = "HOLD"
        ratio = current_vol / avg_vol if avg_vol else 1.0
        conf = self._clamp(abs(ratio - 1.0))
        return AgentVote(
            self.name, signal, conf,
            f"volume={current_vol:.0f}, avg20={avg_vol:.0f}, spread_bps={current_spread:.2f}",
            self.category,
        )


class VolatilityAgent(BaseAgent):
    name = "VolatilityAgent"
    category = "observation"

    def vote(self, state: MarketState) -> AgentVote:
        rv20 = realized_volatility(state.prices, 20)
        rv60 = realized_volatility(state.prices, 60)
        if rv20 is None or rv60 is None:
            return AgentVote(self.name, "HOLD", 0.2, "insufficient volatility history", self.category)
        if rv20 > rv60 * 1.30:
            signal: Signal = "SELL"
        elif rv20 < rv60 * 0.85:
            signal = "BUY"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(rv20 / rv60 - 1.0) * 2) if rv60 else 0.2
        return AgentVote(self.name, signal, conf, f"rv20={rv20:.4f}, rv60={rv60:.4f}", self.category)


class MacroAgent(BaseAgent):
    name = "MacroAgent"
    category = "observation"

    def vote(self, state: MarketState) -> AgentVote:
        score = state.event_risk_scores[-1] if state.event_risk_scores else 0.5
        if score > 0.7:
            signal: Signal = "SELL"
        elif score < 0.3:
            signal = "BUY"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(score - 0.5) * 2)
        return AgentVote(self.name, signal, conf, f"macro_event_risk={score:.2f}", self.category)


# ─── FAMILLE TECHNIQUE / ALPHA ──────────────────────────────────────────────

class MomentumAgent(BaseAgent):
    name = "MomentumAgent"
    category = "technical"

    def vote(self, state: MarketState) -> AgentVote:
        if len(state.prices) < 6:
            return AgentVote(self.name, "HOLD", 0.2, "need 6 prices", self.category)
        now, prev5 = state.prices[-1], state.prices[-6]
        ret5 = (now - prev5) / prev5 if prev5 else 0.0
        rsi14 = rsi(state.prices, 14)
        if ret5 > 0 and (rsi14 is None or rsi14 < 75):
            signal: Signal = "BUY"
        elif ret5 < 0 and (rsi14 is None or rsi14 > 25):
            signal = "SELL"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(ret5) * 20)
        return AgentVote(
            self.name, signal, conf,
            f"5-step return={ret5:.4f}, rsi14={rsi14:.1f}" if rsi14 else f"5-step return={ret5:.4f}",
            self.category,
        )


class MeanReversionAgent(BaseAgent):
    name = "MeanReversionAgent"
    category = "technical"

    def vote(self, state: MarketState) -> AgentVote:
        z = zscore(state.prices, 20)
        lower, mid, upper = bollinger(state.prices, 20, 2.0)
        if z is None or lower is None or upper is None:
            return AgentVote(self.name, "HOLD", 0.2, "need 20 prices", self.category)
        px = state.prices[-1]
        if px < lower or z < -2.0:
            signal: Signal = "BUY"
        elif px > upper or z > 2.0:
            signal = "SELL"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(z) / 3)
        return AgentVote(
            self.name, signal, conf,
            f"zscore20={z:.2f}, bb=({lower:.2f},{upper:.2f})",
            self.category,
        )


class BreakoutAgent(BaseAgent):
    name = "BreakoutAgent"
    category = "technical"

    def vote(self, state: MarketState) -> AgentVote:
        if len(state.prices) < 21:
            return AgentVote(self.name, "HOLD", 0.2, "need 21 prices", self.category)
        last = state.prices[-1]
        resistance = max(list(state.highs)[-20:])
        support = min(list(state.lows)[-20:])
        if last > resistance:
            signal: Signal = "BUY"
        elif last < support:
            signal = "SELL"
        else:
            signal = "HOLD"
        distance = max(abs(last - resistance), abs(last - support)) / last if last else 0.0
        conf = self._clamp(distance * 25)
        return AgentVote(
            self.name, signal, conf,
            f"px={last:.2f}, support={support:.2f}, resistance={resistance:.2f}",
            self.category,
        )


class PatternAgent(BaseAgent):
    name = "PatternAgent"
    category = "technical"

    def vote(self, state: MarketState) -> AgentVote:
        if len(state.prices) < 10:
            return AgentVote(self.name, "HOLD", 0.2, "need 10 prices", self.category)
        seq = list(state.prices)[-5:]
        rises = sum(1 for i in range(1, len(seq)) if seq[i] > seq[i - 1])
        drops = sum(1 for i in range(1, len(seq)) if seq[i] < seq[i - 1])
        # Vérification MACD pour confirmation
        macd_line, signal_line, hist = macd(state.prices)
        macd_confirm = hist is not None and hist > 0
        if rises >= 4 and macd_confirm:
            signal: Signal = "BUY"
        elif drops >= 4:
            signal = "SELL"
        else:
            signal = "HOLD"
        conf = self._clamp(max(rises, drops) / 5)
        return AgentVote(
            self.name, signal, conf,
            f"up={rises}, down={drops}, macd_hist={hist:.4f}" if hist else f"up={rises}, down={drops}",
            self.category,
        )


# ─── FAMILLE CONTEXTE ───────────────────────────────────────────────────────

class SentimentAgent(BaseAgent):
    name = "SentimentAgent"
    category = "context"

    def vote(self, state: MarketState) -> AgentVote:
        score = state.sentiment_scores[-1] if state.sentiment_scores else 0.0
        if score > 0.20:
            signal: Signal = "BUY"
        elif score < -0.20:
            signal = "SELL"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(score))
        return AgentVote(self.name, signal, conf, f"sentiment={score:.2f}", self.category)


class EventAgent(BaseAgent):
    name = "EventAgent"
    category = "context"

    def vote(self, state: MarketState) -> AgentVote:
        risk = state.event_risk_scores[-1] if state.event_risk_scores else 0.0
        if risk > 0.65:
            signal: Signal = "SELL"
        elif risk < 0.25:
            signal = "BUY"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(risk - 0.45) * 1.8)
        return AgentVote(self.name, signal, conf, f"event_risk={risk:.2f}", self.category)


class CorrelationAgent(BaseAgent):
    name = "CorrelationAgent"
    category = "context"

    def vote(self, state: MarketState) -> AgentVote:
        if len(state.btc_reference_prices) < 6 or len(state.prices) < 6:
            return AgentVote(self.name, "HOLD", 0.2, "need 6 reference prices", self.category)
        asset_ret = (state.prices[-1] - state.prices[-6]) / state.prices[-6]
        btc_ret = (state.btc_reference_prices[-1] - state.btc_reference_prices[-6]) / state.btc_reference_prices[-6]
        if asset_ret > 0 and btc_ret > 0:
            signal: Signal = "BUY"
        elif asset_ret < 0 and btc_ret < 0:
            signal = "SELL"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(asset_ret - btc_ret) * 10)
        return AgentVote(
            self.name, signal, conf,
            f"asset_ret={asset_ret:.4f}, btc_ret={btc_ret:.4f}",
            self.category,
        )


# ─── FAMILLE STRATÉGIE ──────────────────────────────────────────────────────

class SignalAggregatorAgent(BaseAgent):
    name = "SignalAggregatorAgent"
    category = "strategy"

    def vote(self, state: MarketState) -> AgentVote:
        return AgentVote(self.name, "HOLD", 0.0, "meta-agent: use aggregate_votes()", self.category)


class PredictionAgent(BaseAgent):
    name = "PredictionAgent"
    category = "strategy"

    def vote(self, state: MarketState) -> AgentVote:
        rv20 = realized_volatility(state.prices, 20)
        risk = state.event_risk_scores[-1] if state.event_risk_scores else 0.0
        spread = state.spreads_bps[-1] if state.spreads_bps else 0.0
        if rv20 is None:
            return AgentVote(self.name, "HOLD", 0.2, "insufficient prediction data", self.category)
        composite = min(1.0, rv20 * 10 + risk * 0.7 + spread / 100)
        if composite > 0.70:
            signal: Signal = "SELL"
        elif composite < 0.35:
            signal = "BUY"
        else:
            signal = "HOLD"
        conf = self._clamp(abs(composite - 0.5) * 2)
        return AgentVote(
            self.name, signal, conf,
            f"composite_risk={composite:.2f} (rv20={rv20:.4f}, event={risk:.2f})",
            self.category,
        )


class PortfolioAgent(BaseAgent):
    name = "PortfolioAgent"
    category = "strategy"

    def __init__(self, exposure: float = 0.0, drawdown: float = 0.0) -> None:
        self.exposure = exposure
        self.drawdown = drawdown

    def vote(self, state: MarketState) -> AgentVote:
        if self.drawdown > 0.10 or self.exposure > 0.80:
            signal: Signal = "SELL"
        elif self.exposure < 0.30 and self.drawdown < 0.03:
            signal = "BUY"
        else:
            signal = "HOLD"
        conf = self._clamp(max(self.drawdown, self.exposure))
        return AgentVote(
            self.name, signal, conf,
            f"exposure={self.exposure:.2f}, drawdown={self.drawdown:.2f}",
            self.category,
        )


# ─── Registre et fonctions utilitaires ─────────────────────────────────────

AGENT_CLASSES = [
    MarketDataAgent, LiquidityAgent, VolatilityAgent, MacroAgent,
    MomentumAgent, MeanReversionAgent, BreakoutAgent, PatternAgent,
    SentimentAgent, EventAgent, CorrelationAgent,
    SignalAggregatorAgent, PredictionAgent, PortfolioAgent,
]


def build_default_agents(*, exposure: float = 0.0, drawdown: float = 0.0) -> List[BaseAgent]:
    agents: List[BaseAgent] = []
    for cls in AGENT_CLASSES:
        if cls is PortfolioAgent:
            agents.append(cls(exposure=exposure, drawdown=drawdown))
        else:
            agents.append(cls())
    return agents


def aggregate_votes(votes: List[AgentVote]) -> dict:
    """Vote pondéré par la confiance. Exclut le SignalAggregatorAgent (meta)."""
    active = [v for v in votes if v.name != "SignalAggregatorAgent"]
    buy_w = sum(v.confidence for v in active if v.signal == "BUY")
    sell_w = sum(v.confidence for v in active if v.signal == "SELL")
    hold_w = sum(v.confidence for v in active if v.signal == "HOLD")
    total = buy_w + sell_w + hold_w
    if total == 0:
        return {"side": "HOLD", "confidence": 0.0, "buy_weight": 0.0, "sell_weight": 0.0, "hold_weight": 0.0}
    if buy_w > max(sell_w, hold_w):
        side, top = "BUY", buy_w
    elif sell_w > max(buy_w, hold_w):
        side, top = "SELL", sell_w
    else:
        side, top = "HOLD", hold_w
    return {
        "side": side,
        "confidence": round(top / total, 4),
        "buy_weight": round(buy_w, 4),
        "sell_weight": round(sell_w, 4),
        "hold_weight": round(hold_w, 4),
    }
