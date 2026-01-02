from datetime import datetime, timedelta, timezone

from ap.memory import MemoryStore


def test_memory_persists_and_retrieves(tmp_path):
    db_path = tmp_path / "memory.db"
    store = MemoryStore(db_path)
    entry_id = store.store_fact("important fact")

    store_again = MemoryStore(db_path)
    results = store_again.retrieve_relevant("important", limit=3)

    assert results
    assert any(entry.id == entry_id for entry in results)


def test_retrieval_ranks_by_recency(tmp_path):
    db_path = tmp_path / "memory.db"
    store = MemoryStore(db_path)
    older = store.store_fact("old detail", importance=0.5, decay_rate=0.1)
    newer = store.store_fact("fresh detail", importance=1.0, decay_rate=0.01)

    # Manually backdate the older entry
    with store._connect() as conn:  # noqa: SLF001 - test-controlled adjustment
        past = int((datetime.now(timezone.utc) - timedelta(hours=5)).timestamp())
        conn.execute("UPDATE memory_entries SET last_accessed=? WHERE id=?", (past, older))
        conn.commit()

    results = store.retrieve_relevant("detail", limit=2)
    assert results
    assert results[0].content == "fresh detail"


def test_forget_removes_entries(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    entry_id = store.store_fact("to forget")
    assert store.forget(entry_id) is True
    assert not store.retrieve_relevant("forget")


def test_forget_nonexistent_is_clean(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    assert store.forget(9999) is False
