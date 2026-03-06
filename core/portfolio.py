"""
Obsidia x ERC-8004 — Portfolio Manager
Gestion du capital, exposition et drawdown.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioState:
    cash: float = 10_000.0   # Capital de test hackathon
    base_units: float = 0.0
    last_price: float = 0.0
    realized_pnl: float = 0.0
    peak_nav: float = 10_000.0

    @property
    def nav(self) -> float:
        return self.cash + self.base_units * self.last_price

    @property
    def drawdown(self) -> float:
        if self.peak_nav <= 0:
            return 0.0
        return max(0.0, (self.peak_nav - self.nav) / self.peak_nav)

    def as_dict(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "base_units": round(self.base_units, 6),
            "last_price": round(self.last_price, 2),
            "nav": round(self.nav, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "drawdown": round(self.drawdown, 4),
        }


class Portfolio:
    def __init__(self, initial_cash: float = 10_000.0) -> None:
        self.state = PortfolioState(cash=initial_cash, peak_nav=initial_cash)

    def exposure(self) -> float:
        nav = max(self.state.nav, 1e-9)
        return (self.state.base_units * self.state.last_price) / nav if self.state.last_price else 0.0

    def as_dict(self) -> dict:
        """Délègue vers PortfolioState.as_dict() pour compatibilité app.py"""
        return self.state.as_dict()

    def apply(self, side: str, price: float, quantity: float, decision: str) -> PortfolioState:
        self.state.last_price = price
        if decision != "ALLOW":
            return self.state

        if side == "BUY":
            cost = quantity * price
            if cost <= self.state.cash:
                self.state.cash -= cost
                self.state.base_units += quantity
                self.state._entry_price = price  # Stocker le prix d'entrée
        elif side == "SELL":
            qty = min(self.state.base_units, quantity)
            proceeds = qty * price
            # PnL = produit de la vente - coût d'entrée (dernier prix d'achat)
            entry_price = getattr(self.state, '_entry_price', price)
            self.state.realized_pnl += (price - entry_price) * qty
            self.state.cash += proceeds
            self.state.base_units -= qty

        # Mise à jour du peak pour le drawdown
        if self.state.nav > self.state.peak_nav:
            self.state.peak_nav = self.state.nav

        return self.state
