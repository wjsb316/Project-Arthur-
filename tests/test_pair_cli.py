from datetime import datetime, timedelta, timezone

import pytest

from ap.cli import approve_request, deny_request, list_pending
from ap.persistence.pairing import PairingRepository


def _repo(tmp_path) -> PairingRepository:
    return PairingRepository(tmp_path / "pair-cli.db")


def _seed(repo: PairingRepository) -> str:
    pair_request_id = "request-1"
    repo.add_pending(
        pair_request_id,
        "ABC123",
        "device-a",
        datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    return pair_request_id


def test_cli_approve_updates_status(tmp_path):
    repo = _repo(tmp_path)
    pair_request_id = _seed(repo)

    approve_request(repo, pair_request_id)
    record = repo.get_by_request_id(pair_request_id)

    assert record is not None
    assert record.status == "approved"


def test_cli_approve_missing_request_raises(tmp_path):
    repo = _repo(tmp_path)

    with pytest.raises(ValueError):
        approve_request(repo, "unknown")


def test_cli_list_pending_returns_entries(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo)

    pending = list(list_pending(repo))

    assert len(pending) == 1
    assert pending[0].pair_request_id == "request-1"
    assert pending[0].status == "pending"


def test_cli_deny_updates_status(tmp_path):
    repo = _repo(tmp_path)
    pair_request_id = _seed(repo)

    deny_request(repo, pair_request_id)
    record = repo.get_by_request_id(pair_request_id)

    assert record is not None
    assert record.status == "denied"

