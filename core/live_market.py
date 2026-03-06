"""
Obsidia x ERC-8004 — Live Market Feed
Connexion à l'API publique Binance pour les données en temps réel.
Fallback sur MockMarketFeed si l'API est indisponible.
"""
from __future__ import annotations

import math
import random
import time
from typing import Optional

import requests

from agents.indicators import MarketState


BINANCE_BASE = "https://api.binance.com/api/v3"
BINANCE_US_BASE = "https://api.binance.us/api/v3"


def _fetch_binance(symbol: str = "BTCUSDT", base: str = BINANCE_BASE) -> Optional[dict]:
    """Récupère le ticker 24h et le carnet d'ordres depuis Binance."""
    try:
        ticker = requests.get(
            f"{base}/ticker/24hr", params={"symbol": symbol}, timeout=5
        ).json()
        book = requests.get(
            f"{base}/depth", params={"symbol": symbol, "limit": 5}, timeout=5
        ).json()
        klines = requests.get(
            f"{base}/klines",
            params={"symbol": symbol, "interval": "1m", "limit": 2},
            timeout=5,
        ).json()
        return {"ticker": ticker, "book": book, "klines": klines}
    except Exception:
        return None


def _parse_binance(raw: dict) -> dict:
    """Parse la réponse Binance en données exploitables."""
    ticker = raw["ticker"]
    book = raw["book"]
    klines = raw["klines"]

    price = float(ticker.get("lastPrice", 0))
    high = float(ticker.get("highPrice", price))
    low = float(ticker.get("lowPrice", price))
    volume = float(ticker.get("volume", 0))
    price_change_pct = float(ticker.get("priceChangePercent", 0)) / 100.0

    # Imbalance carnet d'ordres
    best_bid_qty = float(book["bids"][0][1]) if book.get("bids") else 1.0
    best_ask_qty = float(book["asks"][0][1]) if book.get("asks") else 1.0
    total = best_bid_qty + best_ask_qty
    obi = (best_bid_qty - best_ask_qty) / total if total > 0 else 0.0

    # Spread en bps
    best_bid = float(book["bids"][0][0]) if book.get("bids") else price
    best_ask = float(book["asks"][0][0]) if book.get("asks") else price
    spread_bps = ((best_ask - best_bid) / price * 10000) if price > 0 else 5.0

    # Volatilité sur la dernière minute (high-low / close)
    if klines and len(klines) >= 2:
        k = klines[-1]
        k_high, k_low, k_close = float(k[2]), float(k[3]), float(k[4])
        volatility = (k_high - k_low) / k_close if k_close > 0 else 0.01
    else:
        volatility = abs(price_change_pct) * 2

    return {
        "price": price,
        "high": high,
        "low": low,
        "volume": volume,
        "spread_bps": spread_bps,
        "order_book_imbalance": obi,
        "volatility": min(1.0, volatility * 10),
    }


class LiveMarketFeed:
    """
    Flux de marché live branché sur Binance.
    Met à jour un MarketState à chaque appel de next().
    """

    def __init__(self, symbol: str = "BTCUSDT", use_us: bool = False) -> None:
        self.symbol = symbol
        self._base = BINANCE_US_BASE if use_us else BINANCE_BASE
        self._state = MarketState(symbol=symbol)
        self._mock = MockMarketFeed(symbol=symbol)
        self._use_mock = False

    def next(self) -> MarketState:
        raw = _fetch_binance(self.symbol, self._base)
        if raw is None:
            # Fallback sur mock si API indisponible
            self._use_mock = True
            return self._mock.next()

        self._use_mock = False
        data = _parse_binance(raw)

        # Sentiment proxy : price_change_pct normalisé
        price = data["price"]
        prev = self._state.prices[-1] if self._state.prices else price
        sentiment = min(1.0, max(-1.0, (price - prev) / prev * 50)) if prev else 0.0

        # Event risk proxy : volatilité élevée + volume anormal
        avg_vol = sum(list(self._state.volumes)[-20:]) / 20 if len(self._state.volumes) >= 20 else data["volume"]
        vol_ratio = data["volume"] / avg_vol if avg_vol > 0 else 1.0
        event_risk = min(1.0, data["volatility"] * 0.6 + min(vol_ratio - 1, 1.0) * 0.4)

        self._state.update(
            price=data["price"],
            high=data["high"],
            low=data["low"],
            volume=data["volume"],
            spread_bps=data["spread_bps"],
            order_book_imbalance=data["order_book_imbalance"],
            sentiment_score=sentiment,
            event_risk=max(0.0, event_risk),
            btc_reference_price=data["price"] if "BTC" in self.symbol else None,
        )
        return self._state

    @property
    def is_live(self) -> bool:
        return not self._use_mock


class MockMarketFeed:
    """Flux de marché simulé (fallback / tests)."""

    def __init__(self, symbol: str = "BTCUSDT", seed: int = 7) -> None:
        self.symbol = symbol
        self._rng = random.Random(seed)
        self._price = 65000.0
        self._state = MarketState(symbol=symbol)

    def next(self) -> MarketState:
        prev = self._price
        drift = self._rng.uniform(-0.015, 0.015)
        cyc = 0.005 * math.sin(time.time() / 11.0)
        self._price = max(1000.0, prev * (1 + drift + cyc))
        volatility = min(1.0, abs(drift) * 18 + self._rng.uniform(0.08, 0.22))
        event_risk = min(1.0, self._rng.uniform(0.05, 0.8) * (0.8 if volatility < 0.55 else 1.1))

        self._state.update(
            price=self._price,
            high=self._price * (1 + abs(drift) * 0.5),
            low=self._price * (1 - abs(drift) * 0.5),
            volume=self._rng.uniform(900_000, 4_000_000),
            spread_bps=self._rng.uniform(3, 18),
            order_book_imbalance=self._rng.uniform(-1, 1),
            sentiment_score=self._rng.uniform(-1, 1),
            event_risk=event_risk,
            btc_reference_price=self._price,
        )
        return self._state
