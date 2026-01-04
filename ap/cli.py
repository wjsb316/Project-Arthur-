"""Command-line tools for pairing approvals."""

from __future__ import annotations

import argparse
from typing import Iterable

from .config import load_settings
from .persistence.pairing import PairingRecord, PairingRepository


def list_pending(repository: PairingRepository) -> Iterable[PairingRecord]:
    """Return all pending pairing requests."""
    return repository.list_pending()


def approve_request(repository: PairingRepository, identifier: str) -> None:
    """Approve a specific pairing request by ID or code."""
    if not repository.approve(identifier):
        raise ValueError("pairing request not found")


def deny_request(repository: PairingRepository, identifier: str) -> None:
    """Deny a specific pairing request by ID or code."""
    if not repository.deny(identifier):
        raise ValueError("pairing request not found")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Arthur Prime pairing administration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List pending pairing requests")

    approve_parser = subparsers.add_parser("approve", help="Approve a pairing request")
    approve_parser.add_argument("identifier", help="pair_request_id or pair_code")

    deny_parser = subparsers.add_parser("deny", help="Deny a pairing request")
    deny_parser.add_argument("identifier", help="pair_request_id or pair_code")

    return parser


def _load_repository() -> PairingRepository:
    settings = load_settings()
    return PairingRepository(settings.pairing_db_path)


def main() -> None:  # pragma: no cover - exercised via unit helpers
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()
    repo = _load_repository()

    if args.command == "list":
        for record in list_pending(repo):
            print(  # noqa: T201 - CLI output is intentional
                f"{record.pair_request_id}\t{record.pair_code}\t{record.device_id}\t{record.expires_at.isoformat()}\t{record.status}"
            )
    elif args.command == "approve":
        approve_request(repo, args.identifier)
    elif args.command == "deny":
        deny_request(repo, args.identifier)


if __name__ == "__main__":  # pragma: no cover
    main()
