"""
OTA Payload: HMAC signing and verification for assignment bundles.

Combines:
- External package's HMAC-SHA256 signing
- Local package's manifest-based integrity + zip bundling
"""
from __future__ import annotations

import hashlib
import hmac
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .schemas import PracticeAssignment
from .assignment_serializer import serialize_bundle


# ============================================================================
# Constants
# ============================================================================

OTA_BUNDLE_CONTRACT_VERSION: str = "v1"
HMAC_ALGORITHM = "HS256"


# ============================================================================
# Manifest Schema (for folder/zip bundles)
# ============================================================================


class OtaArtifact(BaseModel):
    """A file shipped inside the bundle."""
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(..., min_length=1)
    kind: Literal["assignment", "attachment"] = "attachment"
    path: str = Field(..., min_length=1)
    sha256: str = Field(..., min_length=64, max_length=64)
    bytes: int = Field(..., ge=0)

    @field_validator("sha256")
    @classmethod
    def _sha_hex(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
            raise ValueError("sha256 must be 64 hex characters")
        return v

    @field_validator("path")
    @classmethod
    def _no_abs_paths(cls, v: str) -> str:
        if v.startswith("/") or v.startswith("\\") or ":" in v:
            raise ValueError("path must be relative")
        return v


class OtaBundleManifest(BaseModel):
    """Manifest for folder/zip OTA bundles."""
    model_config = ConfigDict(extra="forbid")

    manifest_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    contract: str = Field(default=OTA_BUNDLE_CONTRACT_VERSION)
    coach_contract: str = Field(default="v1")

    product: str = Field(default="smart-guitar", min_length=1)
    target_device_model: Optional[str] = None
    target_min_firmware: Optional[str] = None

    assignment_id: UUID
    session_id: UUID

    artifacts: List[OtaArtifact] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)

    @field_validator("artifacts")
    @classmethod
    def _must_have_assignment(cls, v: List[OtaArtifact]) -> List[OtaArtifact]:
        if not any(a.kind == "assignment" and a.artifact_id == "assignment" for a in v):
            raise ValueError("manifest must include assignment artifact_id='assignment'")
        return v


# ============================================================================
# OTA Envelope (for JSON-only transport with HMAC)
# ============================================================================


class OtaEnvelope(BaseModel):
    """Signed envelope for JSON OTA transport."""
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0.0")
    algorithm: str = Field(default=HMAC_ALGORITHM)
    payload: Dict[str, Any]
    signature: Optional[str] = None  # HMAC hex


# ============================================================================
# Signing Functions
# ============================================================================


def _canonical_json(obj: Dict[str, Any]) -> bytes:
    """Produce canonical JSON for signing."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def hmac_sha256_hex(secret: bytes, data: bytes) -> str:
    """Compute HMAC-SHA256 and return hex digest."""
    return hmac.new(secret, data, hashlib.sha256).hexdigest()


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


# ============================================================================
# JSON OTA Payload (HMAC signed)
# ============================================================================


def build_ota_payload(
    assignment: PracticeAssignment,
    *,
    secret: bytes | None = None,
) -> Dict[str, Any]:
    """
    Build OTA payload with optional HMAC signature.

    Args:
        assignment: The assignment to package
        secret: HMAC secret (if None, no signature is added)

    Returns:
        OtaEnvelope as dict
    """
    bundle = serialize_bundle(assignment)

    if secret is not None:
        canon = _canonical_json(bundle)
        sig = hmac_sha256_hex(secret, canon)
    else:
        sig = None

    envelope = OtaEnvelope(
        payload=bundle,
        signature=sig,
    )

    return envelope.model_dump(mode="json")


def verify_ota_payload(
    envelope_data: Dict[str, Any],
    *,
    secret: bytes,
) -> bool:
    """
    Verify HMAC signature of OTA payload.

    Args:
        envelope_data: The envelope dict to verify
        secret: HMAC secret

    Returns:
        True if signature is valid, False otherwise
    """
    envelope = OtaEnvelope.model_validate(envelope_data)

    if envelope.signature is None:
        return False

    if envelope.algorithm != HMAC_ALGORITHM:
        return False

    canon = _canonical_json(envelope.payload)
    expected = hmac_sha256_hex(secret, canon)

    return hmac.compare_digest(envelope.signature, expected)


# ============================================================================
# Folder/Zip Bundle Building
# ============================================================================


@dataclass(frozen=True)
class BundleBuildResult:
    """Result of building an OTA bundle."""
    bundle_dir: Path
    manifest_path: Path
    assignment_path: Path
    signature_path: Optional[Path] = None
    zip_path: Optional[Path] = None


def _write_json(path: Path, obj: object) -> None:
    """Write JSON to file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _zip_bundle_dir(*, bundle_dir: Path, zip_path: Path) -> None:
    """Create a zip of the bundle directory."""
    files = sorted([p for p in bundle_dir.rglob("*") if p.is_file()], key=lambda p: p.as_posix())
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            rel = p.relative_to(bundle_dir).as_posix()
            z.write(p, arcname=rel)


def build_assignment_ota_bundle(
    *,
    assignment: PracticeAssignment,
    out_dir: str | Path,
    bundle_name: Optional[str] = None,
    product: str = "smart-guitar",
    target_device_model: Optional[str] = None,
    target_min_firmware: Optional[str] = None,
    attachments: Optional[Sequence[Tuple[str, bytes]]] = None,
    make_zip: bool = True,
    hmac_secret: Optional[bytes] = None,
) -> BundleBuildResult:
    """
    Build an OTA bundle folder with:
      - manifest.json
      - assignment.json
      - signature.json (with HMAC if secret provided)
      - optional attachments/
      - bundle.zip (optional)

    Args:
        assignment: The practice assignment to bundle
        out_dir: Output directory root
        bundle_name: Optional bundle folder name override
        product: Product name for manifest routing
        target_device_model: Target device model
        target_min_firmware: Target minimum firmware
        attachments: Optional sequence of (relative_name, bytes)
        make_zip: Whether to create bundle.zip
        hmac_secret: Optional HMAC secret for signing

    Returns:
        BundleBuildResult with paths to created files
    """
    out_dir = Path(out_dir)
    if bundle_name is None:
        bundle_name = f"ota_assignment_{assignment.assignment_id}"

    bundle_dir = out_dir / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Write assignment.json
    assignment_path = bundle_dir / "assignment.json"
    assignment_obj = serialize_bundle(assignment)
    _write_json(assignment_path, assignment_obj)

    # Optional attachments
    artifact_list: list[Path] = []
    if attachments:
        attach_root = bundle_dir / "attachments"
        for rel_name, payload in attachments:
            rel_name = rel_name.strip().lstrip("/").lstrip("\\")
            if not rel_name:
                raise ValueError("attachment name cannot be empty")
            p = attach_root / rel_name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(payload)
            artifact_list.append(p)

    # Build artifact list
    artifacts: list[OtaArtifact] = []

    artifacts.append(
        OtaArtifact(
            artifact_id="assignment",
            kind="assignment",
            path="assignment.json",
            sha256=sha256_file(assignment_path),
            bytes=assignment_path.stat().st_size,
        )
    )

    for p in artifact_list:
        rel_path = p.relative_to(bundle_dir).as_posix()
        artifacts.append(
            OtaArtifact(
                artifact_id=f"att:{rel_path}",
                kind="attachment",
                path=rel_path,
                sha256=sha256_file(p),
                bytes=p.stat().st_size,
            )
        )

    # Build and write manifest
    manifest = OtaBundleManifest(
        product=product,
        target_device_model=target_device_model,
        target_min_firmware=target_min_firmware,
        assignment_id=assignment.assignment_id,
        session_id=assignment.session_id,
        artifacts=artifacts,
    )

    manifest_path = bundle_dir / "manifest.json"
    _write_json(manifest_path, manifest.model_dump(mode="json"))

    # Write signature.json
    signature_path = bundle_dir / "signature.json"
    manifest_hash = sha256_file(manifest_path)

    sig_obj: Dict[str, Any] = {
        "subject": "manifest.json",
        "subject_sha256": manifest_hash,
        "algorithm": HMAC_ALGORITHM if hmac_secret else "none",
        "signature": None,
    }

    if hmac_secret:
        # Sign the canonical manifest JSON
        manifest_bytes = manifest_path.read_bytes()
        sig_obj["signature"] = hmac_sha256_hex(hmac_secret, manifest_bytes)

    _write_json(signature_path, sig_obj)

    # Create zip if requested
    zip_path = None
    if make_zip:
        zip_path = out_dir / f"{bundle_name}.zip"
        _zip_bundle_dir(bundle_dir=bundle_dir, zip_path=zip_path)

    return BundleBuildResult(
        bundle_dir=bundle_dir,
        manifest_path=manifest_path,
        assignment_path=assignment_path,
        signature_path=signature_path,
        zip_path=zip_path,
    )


# ============================================================================
# Bundle Verification
# ============================================================================


def verify_bundle_integrity(bundle_dir: str | Path) -> bool:
    """
    Verify bundle integrity by checking manifest hashes.

    Returns True if all artifacts match their declared hashes.
    """
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "manifest.json"

    if not manifest_path.exists():
        return False

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = OtaBundleManifest.model_validate(manifest_data)

    for artifact in manifest.artifacts:
        file_path = bundle_dir / artifact.path
        if not file_path.exists():
            return False

        actual_hash = sha256_file(file_path)
        if actual_hash != artifact.sha256:
            return False

    return True


def verify_bundle_signature(
    bundle_dir: str | Path,
    *,
    secret: bytes,
) -> bool:
    """
    Verify bundle signature.

    Returns True if signature matches.
    """
    bundle_dir = Path(bundle_dir)
    signature_path = bundle_dir / "signature.json"
    manifest_path = bundle_dir / "manifest.json"

    if not signature_path.exists() or not manifest_path.exists():
        return False

    sig_data = json.loads(signature_path.read_text(encoding="utf-8"))

    if sig_data.get("algorithm") == "none":
        return False  # Not signed

    expected_sig = sig_data.get("signature")
    if not expected_sig:
        return False

    manifest_bytes = manifest_path.read_bytes()
    actual_sig = hmac_sha256_hex(secret, manifest_bytes)

    return hmac.compare_digest(expected_sig, actual_sig)


def verify_zip_bundle(
    zip_path: str | Path,
    *,
    secret: Optional[bytes] = None,
    extract_dir: Optional[Path] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Verify a zipped OTA bundle.

    Args:
        zip_path: Path to the zip file
        secret: Optional HMAC secret for signature verification
        extract_dir: Optional extraction directory (uses temp if None)

    Returns:
        Tuple of (success, error_message)
    """
    import tempfile

    zip_path = Path(zip_path)

    if not zip_path.exists():
        return False, f"Zip file not found: {zip_path}"

    if extract_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="ota_verify_")
        extract_dir = Path(temp_dir)
    else:
        extract_dir = Path(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        # Check integrity
        if not verify_bundle_integrity(extract_dir):
            return False, "Bundle integrity check failed"

        # Check signature if secret provided
        if secret is not None:
            if not verify_bundle_signature(extract_dir, secret=secret):
                return False, "Bundle signature verification failed"

        return True, None

    except Exception as e:
        return False, str(e)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Constants
    "OTA_BUNDLE_CONTRACT_VERSION",
    "HMAC_ALGORITHM",
    # Manifest
    "OtaArtifact",
    "OtaBundleManifest",
    # Envelope
    "OtaEnvelope",
    # Functions
    "hmac_sha256_hex",
    "sha256_file",
    "sha256_bytes",
    "build_ota_payload",
    "verify_ota_payload",
    "build_assignment_ota_bundle",
    "verify_bundle_integrity",
    "verify_bundle_signature",
    "verify_zip_bundle",
    "BundleBuildResult",
]
