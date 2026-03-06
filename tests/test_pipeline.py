"""
Obsidia x ERC-8004 — Tests du pipeline complet
Valide que chaque composant fonctionne de bout en bout.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.indicators import MarketState, rsi, macd, bollinger, structural_score
from agents.registry import build_default_agents, aggregate_votes
from core.guard_x108 import GuardX108, GuardDecision
from core.live_market import MockMarketFeed
from core.portfolio import Portfolio
from core.logger import ProofLogger
from blockchain.eip712_signer import EIP712Signer
from blockchain.erc8004_client import ERC8004Client


def test_indicators():
    prices = [100 + i * 0.5 for i in range(50)]  # MACD requires slow+signal=35 points minimum
    assert rsi(prices, 14) is not None
    m, s, h = macd(prices)
    assert m is not None
    lo, mid, hi = bollinger(prices, 20)
    assert lo is not None and lo < mid < hi
    print("✅ indicators OK")


def test_structural_score():
    W = [
        [1.0, 0.8, 0.7],
        [0.8, 1.0, 0.9],
        [0.7, 0.9, 1.0],
    ]
    S = structural_score(W)
    assert S > 0.0
    print(f"✅ structural_score OK — S={S:.4f}")


def test_agents():
    feed = MockMarketFeed(symbol="BTCUSDT")
    for _ in range(50):
        feed.next()
    state = feed.next()
    agents = build_default_agents()
    votes = [a.vote(state) for a in agents]
    assert len(votes) == 14
    consensus = aggregate_votes(votes)
    assert consensus["side"] in ("BUY", "SELL", "HOLD")
    print(f"✅ agents OK — consensus={consensus['side']} conf={consensus['confidence']:.3f}")


def test_guard_x108():
    feed = MockMarketFeed(symbol="BTCUSDT")
    for _ in range(80):
        feed.next()
    state = feed.next()
    agents = build_default_agents()
    votes = [a.vote(state) for a in agents]
    consensus = aggregate_votes(votes)
    guard = GuardX108(min_wait_s=0.0)  # Désactiver le verrou temporel pour le test
    result = guard.evaluate(
        votes=votes,
        consensus=consensus,
        snapshot_volatility=0.2,
        snapshot_event_risk=0.3,
        exposure=0.1,
        drawdown=0.01,
        prediction_risk=0.2,
    )
    assert result.decision in (GuardDecision.ALLOW, GuardDecision.HOLD, GuardDecision.BLOCK)
    assert "artifact_hash" in result.validation_artifact
    print(f"✅ guard_x108 OK — decision={result.decision.value} S={result.structural_S:.4f}")


def test_portfolio():
    p = Portfolio(initial_cash=10_000.0)
    p.apply("BUY", 65000.0, 0.01, "ALLOW")
    assert p.state.base_units > 0
    assert p.state.cash < 10_000.0
    p.apply("SELL", 66000.0, 0.01, "ALLOW")
    assert p.state.realized_pnl > 0
    print(f"✅ portfolio OK — nav={p.state.nav:.2f} pnl={p.state.realized_pnl:.2f}")


def test_eip712():
    signer = EIP712Signer(private_key="demo-key")
    signed = signer.sign_trade_intent(
        symbol="BTCUSDT", side="BUY", quantity=0.01,
        price=65000.0, confidence=0.72,
        artifact_hash="a" * 64, agent_id="obsidia-test",
    )
    assert "signature" in signed
    assert signed["scheme"].startswith("EIP-712")
    print(f"✅ eip712 OK — scheme={signed['scheme']}")


def test_erc8004():
    client = ERC8004Client()
    from config.settings import AGENT_PROFILE
    identity = client.register_identity(AGENT_PROFILE)
    assert identity["status"] == "registered"
    validation = client.submit_validation({"artifact_hash": "a" * 64})
    assert validation["status"] == "validated"
    print(f"✅ erc8004 OK — agent_id={identity['agent_id']}")


def test_proof_logger(tmp_path=None):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        logger = ProofLogger(path=d)
        result = logger.write({"test": True, "cycle": 1})
        assert "hash" in result
        assert len(result["hash"]) == 64
        print(f"✅ proof_logger OK — hash={result['hash'][:12]}...")


def test_full_pipeline():
    """Test du pipeline complet : market → agents → guard → erc8004 → portfolio → log"""
    feed = MockMarketFeed(symbol="BTCUSDT")
    for _ in range(100):
        feed.next()
    state = feed.next()

    agents = build_default_agents(exposure=0.0, drawdown=0.0)
    votes = [a.vote(state) for a in agents]
    consensus = aggregate_votes(votes)

    guard = GuardX108(min_wait_s=0.0)
    result = guard.evaluate(
        votes=votes, consensus=consensus,
        snapshot_volatility=0.2, snapshot_event_risk=0.3,
        exposure=0.0, drawdown=0.0, prediction_risk=0.2,
    )

    signer = EIP712Signer(private_key="demo-key")
    signed = signer.sign_trade_intent(
        symbol="BTCUSDT", side=consensus["side"],
        quantity=0.01, price=state.prices[-1],
        confidence=consensus["confidence"],
        artifact_hash=result.validation_artifact.get("artifact_hash", "a" * 64),
    )

    client = ERC8004Client()
    from config.settings import AGENT_PROFILE
    identity = client.register_identity(AGENT_PROFILE)
    validation = client.submit_validation(result.validation_artifact)
    router = client.route_trade_intent(signed)

    portfolio = Portfolio()
    portfolio.apply(consensus["side"], state.prices[-1], 0.01, result.decision.value)

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        logger = ProofLogger(path=d)
        proof = logger.write({
            "decision": result.decision.value,
            "consensus": consensus,
            "validation": validation,
            "router": router,
        })
        assert "hash" in proof

    print(f"✅ FULL PIPELINE OK — decision={result.decision.value} side={consensus['side']}")


if __name__ == "__main__":
    print("\n🔮 Obsidia x ERC-8004 — Test Suite\n" + "=" * 50)
    test_indicators()
    test_structural_score()
    test_agents()
    test_guard_x108()
    test_portfolio()
    test_eip712()
    test_erc8004()
    test_proof_logger()
    test_full_pipeline()
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED")
