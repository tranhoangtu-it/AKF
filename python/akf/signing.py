"""AKF v1.1 — Cryptographic signing and verification using Ed25519."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from .models import AKF

# Fields to strip from canonical representation before signing
_SIGNATURE_FIELDS = {"signature", "signature_algorithm", "public_key_id", "signed_at", "signed_by",
                     "sig", "sig_algo", "key_id", "sig_at", "sig_by"}


def _load_crypto():
    """Lazy-load cryptography library with helpful error."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
        from cryptography.hazmat.primitives import serialization
        return Ed25519PrivateKey, Ed25519PublicKey, serialization
    except ImportError:
        raise ImportError(
            "Cryptographic signing requires the 'cryptography' package. "
            "Install it with: pip install akf[crypto]"
        )


def keygen(key_dir: Optional[str] = None, name: str = "default") -> Tuple[str, str]:
    """Generate an Ed25519 keypair and save to disk.

    Args:
        key_dir: Directory for keys. Defaults to ~/.akf/keys/.
        name: Key name prefix.

    Returns:
        Tuple of (private_key_path, public_key_path).
    """
    Ed25519PrivateKey, _, serialization = _load_crypto()

    if key_dir is None:
        key_dir = str(Path.home() / ".akf" / "keys")
    Path(key_dir).mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_path = os.path.join(key_dir, f"{name}.pem")
    pub_path = os.path.join(key_dir, f"{name}.pub.pem")

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(priv_path, "wb") as f:
        f.write(priv_bytes)
    os.chmod(priv_path, 0o600)

    with open(pub_path, "wb") as f:
        f.write(pub_bytes)

    return priv_path, pub_path


def key_id_from_public(pub_pem_bytes: bytes) -> str:
    """Compute SHA-256 fingerprint of a public key PEM."""
    return "sha256:" + hashlib.sha256(pub_pem_bytes).hexdigest()[:32]


def _canonical_bytes(unit: AKF) -> bytes:
    """Produce canonical JSON bytes for signing (sorted keys, no signature fields)."""
    d = unit.to_dict(compact=False)
    for field in _SIGNATURE_FIELDS:
        d.pop(field, None)
    return json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sign(unit: AKF, private_key_path: str, signer: Optional[str] = None) -> AKF:
    """Sign an AKF unit with an Ed25519 private key.

    Args:
        unit: AKF unit to sign.
        private_key_path: Path to PEM-encoded Ed25519 private key.
        signer: Signer identifier (email or agent ID).

    Returns:
        New AKF unit with signature fields populated.
    """
    _, _, serialization = _load_crypto()

    with open(private_key_path, "rb") as f:
        priv_bytes = f.read()

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    private_key = serialization.load_pem_private_key(priv_bytes, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Key is not an Ed25519 private key")

    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    canonical = _canonical_bytes(unit)
    sig_bytes = private_key.sign(canonical)
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    # Use field names (not aliases) for model_copy
    return unit.model_copy(update={
        "signature": sig_b64,
        "signature_algorithm": "ed25519",
        "public_key_id": key_id_from_public(pub_pem),
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "signed_by": signer or "unknown",
    })


def verify(unit: AKF, public_key_path: str) -> bool:
    """Verify the Ed25519 signature on an AKF unit.

    Args:
        unit: Signed AKF unit.
        public_key_path: Path to PEM-encoded Ed25519 public key.

    Returns:
        True if signature is valid.

    Raises:
        ValueError: If signature is missing or invalid.
    """
    _, _, serialization = _load_crypto()

    if not unit.signature:
        raise ValueError("Unit has no signature")

    with open(public_key_path, "rb") as f:
        pub_bytes = f.read()

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    public_key = serialization.load_pem_public_key(pub_bytes)
    if not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("Key is not an Ed25519 public key")

    canonical = _canonical_bytes(unit)
    sig_bytes = base64.b64decode(unit.signature)

    from cryptography.exceptions import InvalidSignature
    try:
        public_key.verify(sig_bytes, canonical)
        return True
    except InvalidSignature:
        raise ValueError("Signature verification failed — data may have been tampered with")
