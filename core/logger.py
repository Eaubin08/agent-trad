"""
Obsidia x ERC-8004 — Proof Logger
Enregistre chaque décision de trading avec son hash SHA-256.
Ces logs constituent les preuves d'audit pour le hackathon.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class ProofLogger:
    def __init__(self, path: str = "logs") -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        envelope = {
            "hash": digest,
            "recorded_at": int(time.time()),
            "payload": payload,
        }
        fname = self.path / f"proof_{envelope['recorded_at']}_{digest[:8]}.json"
        fname.write_text(json.dumps(envelope, indent=2, default=str), encoding="utf-8")
        return {"file": str(fname), "hash": digest, "recorded_at": envelope["recorded_at"]}
