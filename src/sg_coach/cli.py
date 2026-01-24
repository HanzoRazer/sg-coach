"""
Smart Guitar Coach CLI.

Commands:
- sgc export-bundle: Build firmware envelope from evaluation + assignment
- sgc ota-pack: Build OTA payload with HMAC signature
- sgc ota-verify: Verify HMAC-signed OTA payload
- sgc ota-bundle: Build OTA folder/zip bundle from SessionRecord
- sgc ota-verify-zip: Verify bundle.zip integrity
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from .schemas import ProgramRef, ProgramType, SessionRecord
from .coach_policy import evaluate_session
from .assignment_policy import plan_assignment
from .assignment_serializer import serialize_bundle
from .ota_payload import (
    build_ota_payload,
    verify_ota_payload,
    build_assignment_ota_bundle,
    verify_bundle_integrity,
    verify_zip_bundle,
)


def _read_text(path: str | Path) -> str:
    """Read text from a file, raising FileNotFoundError if missing."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return p.read_text(encoding="utf-8")


def _read_json(path: str | Path) -> dict:
    """Read JSON from a file."""
    return json.loads(_read_text(path))


def _find_bundle_root(extract_dir: Path) -> Path:
    """
    Find the directory containing manifest.json.
    
    Supports:
      - zip with files at root
      - zip with a single top-level folder
    """
    if (extract_dir / "manifest.json").exists():
        return extract_dir

    matches = list(extract_dir.rglob("manifest.json"))
    if not matches:
        raise ValueError("manifest.json not found in zip")
    if len(matches) > 1:
        raise ValueError("multiple manifest.json found in zip (ambiguous)")
    return matches[0].parent


# ============================================================================
# Commands: Export Bundle (JSON envelope)
# ============================================================================


def cmd_export_bundle(args: argparse.Namespace) -> int:
    """
    Build firmware envelope from session -> evaluation -> assignment.
    Outputs JSON to stdout or file.
    """
    session_json = _read_text(args.session)
    session = SessionRecord.model_validate_json(session_json)

    ev = evaluate_session(session)

    # Build program ref (use session's program if available)
    program = session.program_ref

    assignment = plan_assignment(ev, program)
    bundle = serialize_bundle(assignment)

    output = json.dumps(bundle, indent=2, sort_keys=True)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(output)

    return 0


# ============================================================================
# Commands: OTA Pack (HMAC signed JSON)
# ============================================================================


def cmd_ota_pack(args: argparse.Namespace) -> int:
    """
    Build HMAC-signed OTA payload from session.
    """
    session_json = _read_text(args.session)
    session = SessionRecord.model_validate_json(session_json)

    ev = evaluate_session(session)
    program = session.program_ref
    assignment = plan_assignment(ev, program)

    # Read secret if provided
    secret = None
    if args.secret:
        secret = args.secret.encode("utf-8")
    elif args.secret_file:
        secret = Path(args.secret_file).read_bytes().strip()

    payload = build_ota_payload(assignment, secret=secret)

    output = json.dumps(payload, indent=2, sort_keys=True)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(output)

    return 0


def cmd_ota_verify_hmac(args: argparse.Namespace) -> int:
    """
    Verify HMAC signature of OTA payload.
    """
    payload_json = _read_text(args.payload)
    payload = json.loads(payload_json)

    # Read secret
    if args.secret:
        secret = args.secret.encode("utf-8")
    elif args.secret_file:
        secret = Path(args.secret_file).read_bytes().strip()
    else:
        print("ERROR: --secret or --secret-file required", file=sys.stderr)
        return 1

    if verify_ota_payload(payload, secret=secret):
        print("OK: signature valid")
        return 0
    else:
        print("FAIL: signature invalid or missing")
        return 1


# ============================================================================
# Commands: OTA Bundle (folder/zip)
# ============================================================================


def cmd_ota_bundle(args: argparse.Namespace) -> int:
    """
    Build an OTA bundle folder/zip from a SessionRecord JSON.
    Mode 1 pipeline: SessionRecord -> CoachEvaluation -> PracticeAssignment -> OTA bundle.
    """
    session_json = _read_text(args.session)
    session = SessionRecord.model_validate_json(session_json)

    ev = evaluate_session(session)
    program = session.program_ref
    assignment = plan_assignment(ev, program)

    make_zip = bool(args.zip)

    # HMAC secret if provided
    hmac_secret = None
    if args.secret:
        hmac_secret = args.secret.encode("utf-8")
    elif args.secret_file:
        hmac_secret = Path(args.secret_file).read_bytes().strip()

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=args.out,
        bundle_name=args.name,
        product=args.product,
        target_device_model=args.device_model,
        target_min_firmware=args.min_firmware,
        attachments=None,
        make_zip=make_zip,
        hmac_secret=hmac_secret,
    )

    print(str(res.bundle_dir))
    if res.zip_path is not None:
        print(str(res.zip_path))

    return 0


def cmd_ota_verify_folder(args: argparse.Namespace) -> int:
    """
    Verify an OTA bundle directory (folder form).
    """
    bundle_dir = Path(args.bundle_dir)

    if not verify_bundle_integrity(bundle_dir):
        print("FAIL: bundle integrity check failed")
        return 1

    print("OK")
    return 0


def cmd_ota_verify_zip(args: argparse.Namespace) -> int:
    """
    Verify a bundle.zip by extracting to a temp dir and verifying.
    """
    zip_path = Path(args.zip_path)

    # Read secret if provided
    secret = None
    if args.secret:
        secret = args.secret.encode("utf-8")
    elif args.secret_file:
        secret = Path(args.secret_file).read_bytes().strip()

    success, error = verify_zip_bundle(zip_path, secret=secret)

    if success:
        print("OK")
        return 0
    else:
        print(f"FAIL: {error}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="sgc",
        description="Smart Guitar Coach CLI (Mode 1 / OTA tools)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- export-bundle ---
    p_e = sub.add_parser("export-bundle", help="Build firmware envelope JSON from SessionRecord.")
    p_e.add_argument("--session", required=True, help="Path to session.json (SessionRecord).")
    p_e.add_argument("--output", "-o", default=None, help="Output file (stdout if omitted).")
    p_e.set_defaults(func=cmd_export_bundle)

    # --- ota-pack ---
    p_p = sub.add_parser("ota-pack", help="Build HMAC-signed OTA payload JSON.")
    p_p.add_argument("--session", required=True, help="Path to session.json (SessionRecord).")
    p_p.add_argument("--secret", default=None, help="HMAC secret string.")
    p_p.add_argument("--secret-file", default=None, help="Path to file containing HMAC secret.")
    p_p.add_argument("--output", "-o", default=None, help="Output file (stdout if omitted).")
    p_p.set_defaults(func=cmd_ota_pack)

    # --- ota-verify (HMAC) ---
    p_vh = sub.add_parser("ota-verify", help="Verify HMAC signature of OTA payload JSON.")
    p_vh.add_argument("payload", help="Path to OTA payload JSON file.")
    p_vh.add_argument("--secret", default=None, help="HMAC secret string.")
    p_vh.add_argument("--secret-file", default=None, help="Path to file containing HMAC secret.")
    p_vh.set_defaults(func=cmd_ota_verify_hmac)

    # --- ota-bundle ---
    p_b = sub.add_parser("ota-bundle", help="Build assignment OTA bundle folder/zip from SessionRecord.")
    p_b.add_argument("--session", required=True, help="Path to session.json (SessionRecord).")
    p_b.add_argument("--out", required=True, help="Output directory root.")
    p_b.add_argument("--name", default=None, help="Optional bundle folder name override.")
    p_b.add_argument("--product", default="smart-guitar", help="Product name (manifest routing).")
    p_b.add_argument("--device-model", default=None, help="Target device model.")
    p_b.add_argument("--min-firmware", default=None, help="Target minimum firmware.")
    p_b.add_argument("--zip", action="store_true", help="Also create bundle.zip.")
    p_b.add_argument("--secret", default=None, help="HMAC secret for signing.")
    p_b.add_argument("--secret-file", default=None, help="Path to file containing HMAC secret.")
    p_b.set_defaults(func=cmd_ota_bundle)

    # --- ota-verify-folder ---
    p_vf = sub.add_parser("ota-verify-folder", help="Verify bundle folder integrity against manifest.")
    p_vf.add_argument("bundle_dir", help="Path to bundle directory (folder).")
    p_vf.set_defaults(func=cmd_ota_verify_folder)

    # --- ota-verify-zip ---
    p_z = sub.add_parser("ota-verify-zip", help="Verify bundle.zip by extracting and verifying.")
    p_z.add_argument("zip_path", help="Path to bundle.zip")
    p_z.add_argument("--secret", default=None, help="HMAC secret for signature verification.")
    p_z.add_argument("--secret-file", default=None, help="Path to file containing HMAC secret.")
    p_z.set_defaults(func=cmd_ota_verify_zip)

    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except FileNotFoundError as e:
        print(f"ERROR: file not found: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
