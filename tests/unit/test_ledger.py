from mcp_servers.marketplace import ledger


def test_idempotency_and_append_only_audit():
    ledger.remember("k-test-1", {"ok": 1})
    ledger.remember("k-test-1", {"ok": 2})
    assert ledger.seen("k-test-1") == {"ok": 1}
    ledger.audit("u", "t", {"email": "x@y.com"}, {"r": 1}, "trace")
    import sqlite3
    c = sqlite3.connect(ledger.DB)
    try:
        c.execute("DELETE FROM audit")
        raise AssertionError("audit rows must not be deletable")
    except sqlite3.DatabaseError:
        pass
    assert "x@y.com" not in str(c.execute("SELECT args FROM audit").fetchall())
