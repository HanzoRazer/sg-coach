"""
OTA payload wrapper for sg_coach bundles.

Provides:
- SHA256 digest for integrity checking
- Optional HMAC-SHA256 signing (Gen-1 prototyping)
- Deterministic JSON encoding for repeatable digests
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple


def _iso_z(dt: datetime) -> str:
    """Convert datetime to ISO-8601 with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    s = dt.isoformat(timespec="seconds")
    return s.replace("+00:00", "Z")


def _stable_dumps(obj: Dict[str, Any]) -> str:
    """Compact + deterministic (critical for repeatable digests)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Compute SHA256 hex digest of UTF-8 encoded text."""
    return sha256_bytes(text.encode("utf-8"))


def hmac_sha256_hex(key: bytes, msg: bytes) -> str:
    """Compute HMAC-SHA256 hex digest."""
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class OtaEnvelope:
    """
    OTA wrapper for a coaching bundle.

    Goal:
      - keep the inner bundle stable (sg_coach_bundle v1)
      - add OTA metadata outside it (device can validate cheaply)
      - allow optional signing later without changing bundle schema
    """

    kind: Literal["sg_ota_payload"] = "sg_ota_payload"
    schema_version: str = "v1"
    created_at_utc: Optional[datetime] = None

    # semver-ish strings; device can enforce min/max compatibility.
    coach_version: str = "coach-rules@0.1.0"
    engine_contract: str = "zt-band-rt@v1"

    def to_header(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "created_at": _iso_z(self.created_at_utc or datetime.now(timezone.utc)),
            "coach_version": self.coach_version,
            "engine_contract": self.engine_contract,
        }


def build_ota_payload(
    *,
    bundle_obj: Dict[str, Any],
    envelope: Optional[OtaEnvelope] = None,
    signer_key: Optional[bytes] = None,
    signer_kid: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Wrap an existing sg_coach_bundle JSON object into an OTA payload.

    The payload includes:
      - header (ota metadata)
      - bundle (unchanged object)
      - digest (sha256 of bundle in stable JSON form)
      - optional signature (HMAC-SHA256 for Gen-1)

    Notes:
      - HMAC is intentionally simple for Gen-1 prototyping. You can swap to Ed25519
        later without changing the bundle itself.
    """
    env = envelope or OtaEnvelope()

    # Compute digest over canonical JSON encoding of the bundle object.
    bundle_json = _stable_dumps(bundle_obj)
    bundle_sha = sha256_text(bundle_json)

    out: Dict[str, Any] = {
        "header": env.to_header(),
        "bundle_sha256": bundle_sha,
        "bundle": bundle_obj,
    }

    if signer_key is not None:
        kid = signer_kid or "dev-hmac"
        sig = hmac_sha256_hex(signer_key, bundle_json.encode("utf-8"))
        out["signature"] = {
            "alg": "HS256",
            "kid": kid,
            "sig": sig,
        }

    return out


def verify_ota_payload(
    payload_obj: Dict[str, Any],
    *,
    signer_key: Optional[bytes] = None,
) -> Tuple[bool, str]:
    """
    Verify:
      1) bundle_sha256 matches bundle
      2) if signature present and signer_key provided, verify HS256 signature
    """
    if "bundle" not in payload_obj or "bundle_sha256" not in payload_obj:
        return False, "missing bundle or bundle_sha256"

    bundle = payload_obj["bundle"]
    if not isinstance(bundle, dict):
        return False, "bundle must be an object"

    bundle_json = _stable_dumps(bundle)
    want_sha = payload_obj["bundle_sha256"]
    got_sha = sha256_text(bundle_json)
    if want_sha != got_sha:
        return False, "bundle_sha256 mismatch"

    sig = payload_obj.get("signature")
    if sig is None:
        return True, "ok (unsigned)"

    if signer_key is None:
        return True, "ok (signature present, key not provided)"

    if not isinstance(sig, dict):
        return False, "signature must be an object"

    if sig.get("alg") != "HS256":
        return False, "unsupported signature alg"

    want = sig.get("sig")
    if not isinstance(want, str):
        return False, "missing signature.sig"

    got = hmac_sha256_hex(signer_key, bundle_json.encode("utf-8"))
    if not hmac.compare_digest(want, got):
        return False, "signature mismatch"

    return True, "ok (signed)"


def read_json(path: str | Path) -> Dict[str, Any]:
    """Read a JSON file and return as dict."""
    p = Path(path)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object at root: {p}")
    return obj


def write_json(path: str | Path, obj: Dict[str, Any], *, pretty: bool = False) -> Path:
    """Write a dict as JSON to a file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        txt = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    else:
        txt = _stable_dumps(obj) + "\n"
    p.write_text(txt, encoding="utf-8")
    return p
