"""AKF v1.0 — Provenance chain management and integrity hashing."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import AKF, ProvHop


_HOP_COMPACT_KEYS = {
    "actor": "by",
    "action": "do",
    "timestamp": "at",
    "hash": "h",
    "penalty": "pen",
    "claims_added": "adds",
    "claims_removed": "drops",
    "model": "m",
    "input_hash": "in_h",
    "output_hash": "out_h",
    "duration_ms": "dur",
    "tool_calls": "tools",
}


def _normalize_hop_keys(hop: dict) -> dict:
    """Normalize a hop dict to use compact keys for consistent hashing."""
    result = {}
    for k, v in hop.items():
        new_key = _HOP_COMPACT_KEYS.get(k, k)
        result[new_key] = v
    return result


def compute_hop_hash(previous_hash: Optional[str], hop: dict) -> str:
    """Compute SHA-256 hash for a provenance hop, chained to previous."""
    normalized = _normalize_hop_keys(hop)
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    if previous_hash:
        payload = previous_hash + "|" + payload
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return "sha256:{}".format(digest)


def compute_integrity_hash(unit: AKF) -> str:
    """Compute SHA-256 of entire unit contents (excluding the hash field)."""
    d = unit.to_dict()
    d.pop("hash", None)
    d.pop("integrity_hash", None)
    payload = json.dumps(d, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return "sha256:{}".format(digest)


def validate_chain(prov: List[ProvHop]) -> bool:
    """Verify hop numbers are sequential starting at 0."""
    for i, hop in enumerate(prov):
        if hop.hop != i:
            return False
    return True


def add_hop(
    unit: AKF,
    by: str,
    action: str,
    adds: Optional[List[str]] = None,
    drops: Optional[List[str]] = None,
    penalty: Optional[float] = None,
    model: Optional[str] = None,
) -> AKF:
    """Add a new provenance hop to an existing unit. Auto-hashes."""
    existing = list(unit.prov) if unit.prov else []
    hop_num = len(existing)
    prev_hash = existing[-1].hash if existing and existing[-1].hash else None

    hop_data: Dict = {
        "hop": hop_num,
        "by": by,
        "do": action,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if adds:
        hop_data["adds"] = adds
    if drops:
        hop_data["drops"] = drops
    if penalty is not None:
        hop_data["pen"] = penalty
    if model is not None:
        hop_data["model"] = model

    hop_hash = compute_hop_hash(prev_hash, hop_data)
    hop_data["h"] = hop_hash

    new_hop = ProvHop(**hop_data)
    new_prov = existing + [new_hop]
    updated = unit.model_copy(update={"prov": new_prov})

    # Recompute integrity hash
    integrity = compute_integrity_hash(updated)
    updated = updated.model_copy(update={"integrity_hash": integrity})

    return updated


def models_used(unit: AKF) -> List[str]:
    """Collect all unique model identifiers used in a unit.

    Checks unit.model, claim origins, and provenance hops.
    """
    models: Dict[str, None] = {}

    # Unit-level model
    if unit.model:
        models[unit.model] = None

    # Per-claim origin models
    for claim in unit.claims:
        if claim.origin and claim.origin.model:
            models[claim.origin.model] = None

    # Provenance hop models
    if unit.prov:
        for hop in unit.prov:
            if hop.model:
                models[hop.model] = None

    return list(models.keys())


def format_tree(unit: AKF) -> str:
    """Return a pretty-printed provenance tree string."""
    if not unit.prov:
        return "(no provenance)"

    lines: list = []
    for i, hop in enumerate(unit.prov):
        h_short = hop.hash[:18] + "..." if hop.hash else ""

        adds_str = ""
        if hop.claims_added:
            adds_str = " (+{} claims)".format(len(hop.claims_added))
        drops_str = ""
        if hop.claims_removed:
            drops_str = " (-{} rejected)".format(len(hop.claims_removed))

        if i == 0:
            prefix = ""
        else:
            prefix = "  " * i + "\u2514\u2192 "

        lines.append(
            "{}{} {}{}{} \u2014 {}".format(
                prefix, hop.actor, hop.action, adds_str, drops_str, h_short
            )
        )

    return "\n".join(lines)
