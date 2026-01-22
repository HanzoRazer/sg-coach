"""
sg-coach CLI: Smart Guitar coaching utilities (Mode 1 rules-first).

Commands:
    export-bundle   Read SessionRecord JSON and emit OTA bundle JSON
    ota-pack        Wrap bundle into OTA payload with SHA256 + optional HMAC
    ota-verify      Verify OTA payload integrity and signature
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .assignment_policy import plan_assignment
from .assignment_serializer import dump_json_file, serialize_bundle
from .schemas import CoachEvaluation, PracticeAssignment, SessionRecord
from .ota_payload import OtaEnvelope, build_ota_payload, read_json, verify_ota_payload, write_json


def _read_json(path: str | Path) -> Dict[str, Any]:
    """Read and validate a JSON file as a dict."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object at root of {p}")
    return obj


def _ensure_parent(path: str | Path) -> None:
    """Create parent directories if needed."""
    p = Path(path)
    if p.parent and str(p.parent) not in (".", ""):
        p.parent.mkdir(parents=True, exist_ok=True)


def _evaluate_session_safe(session: SessionRecord) -> CoachEvaluation:
    """
    Evaluate session, importing coach_policy only when needed.
    This avoids circular imports if coach_policy grows.
    """
    from .coach_policy import evaluate_session
    return evaluate_session(session)


def cmd_export_bundle(args: argparse.Namespace) -> int:
    """
    sg-coach export-bundle --in session.json --out bundle.json

    Input: a JSON object matching SessionRecord (JSON-safe)
    Output: an OTA-safe bundle JSON (Session -> CoachEvaluation -> PracticeAssignment)
    """
    try:
        session_dict = _read_json(args.in_path)
        session = SessionRecord.model_validate(session_dict)

        evaluation: CoachEvaluation = _evaluate_session_safe(session)
        assignment: PracticeAssignment = plan_assignment(session=session, evaluation=evaluation)

        bundle = serialize_bundle(session=session, evaluation=evaluation, assignment=assignment)
        _ensure_parent(args.out_path)
        dump_json_file(args.out_path, bundle, pretty=bool(args.pretty))
        return 0
    except Exception as e:
        # Keep failure surface stable for scripting/CI.
        msg = f"[sg-coach] export-bundle failed: {e}"
        print(msg, file=sys.stderr)
        return 2


def cmd_ota_pack(args: argparse.Namespace) -> int:
    """
    sg-coach ota-pack --bundle bundle.json --out payload.json
    Optionally sign with HS256 for Gen-1: --hmac-key HEX --kid dev-hmac
    """
    try:
        bundle = read_json(args.bundle_path)

        key: bytes | None = None
        if args.hmac_key is not None:
            key = bytes.fromhex(args.hmac_key)

        env = OtaEnvelope(
            coach_version=args.coach_version,
            engine_contract=args.engine_contract,
        )
        payload = build_ota_payload(
            bundle_obj=bundle,
            envelope=env,
            signer_key=key,
            signer_kid=args.kid,
        )
        write_json(args.out_path, payload, pretty=bool(args.pretty))
        return 0
    except Exception as e:
        print(f"[sg-coach] ota-pack failed: {e}", file=sys.stderr)
        return 2


def cmd_ota_verify(args: argparse.Namespace) -> int:
    """
    sg-coach ota-verify --payload payload.json [--hmac-key HEX]
    """
    try:
        payload = read_json(args.payload_path)
        key: bytes | None = None
        if args.hmac_key is not None:
            key = bytes.fromhex(args.hmac_key)
        ok, reason = verify_ota_payload(payload, signer_key=key)
        if ok:
            print(f"ok: {reason}")
            return 0
        print(f"fail: {reason}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"[sg-coach] ota-verify failed: {e}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    """Build the sg-coach argument parser."""
    p = argparse.ArgumentParser(
        prog="sg-coach",
        description="Smart Guitar coaching utilities (Mode 1 rules-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # export-bundle
    p_exp = sub.add_parser(
        "export-bundle",
        help="Read SessionRecord JSON and emit OTA bundle JSON (Session->Coach->Assignment).",
    )
    p_exp.add_argument(
        "--in",
        dest="in_path",
        required=True,
        help="Path to session.json (must match SessionRecord JSON shape).",
    )
    p_exp.add_argument(
        "--out",
        dest="out_path",
        required=True,
        help="Path to write bundle.json.",
    )
    p_exp.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON (indent=2). Default is compact deterministic JSON.",
    )
    p_exp.set_defaults(func=cmd_export_bundle)

    # ota-pack
    p_pack = sub.add_parser(
        "ota-pack",
        help="Wrap bundle.json into an OTA payload with sha256 (and optional HS256 signature).",
    )
    p_pack.add_argument(
        "--bundle",
        dest="bundle_path",
        required=True,
        help="Path to bundle.json (sg_coach_bundle v1).",
    )
    p_pack.add_argument(
        "--out",
        dest="out_path",
        required=True,
        help="Path to write payload.json.",
    )
    p_pack.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON.",
    )
    p_pack.add_argument(
        "--coach-version",
        default="coach-rules@0.1.0",
        help="Coach version string to embed in header.",
    )
    p_pack.add_argument(
        "--engine-contract",
        default="zt-band-rt@v1",
        help="Engine contract string to embed in header.",
    )
    p_pack.add_argument(
        "--hmac-key",
        default=None,
        help="Hex-encoded HMAC key (HS256) for signing (optional).",
    )
    p_pack.add_argument(
        "--kid",
        default="dev-hmac",
        help="Key id for signature header (default: dev-hmac).",
    )
    p_pack.set_defaults(func=cmd_ota_pack)

    # ota-verify
    p_ver = sub.add_parser(
        "ota-verify",
        help="Verify OTA payload: sha256 integrity and optional HS256 signature.",
    )
    p_ver.add_argument(
        "--payload",
        dest="payload_path",
        required=True,
        help="Path to payload.json.",
    )
    p_ver.add_argument(
        "--hmac-key",
        default=None,
        help="Hex-encoded HMAC key to verify signature (optional).",
    )
    p_ver.set_defaults(func=cmd_ota_verify)

    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    fn = getattr(args, "func", None)
    if fn is None:
        parser.print_help()
        return 2
    return int(fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
