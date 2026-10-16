"""Fake payment provider persisted per scenario; honours idempotency keys like Stripe."""
import json, os
def _db():
    p = os.environ.get("AS_SCENARIO", "/tmp/agentsignal") + ".provider.json"
    return p, (json.load(open(p)) if os.path.exists(p) else {"n": 0, "keys": {}})
def charge(amount, idempotency_key=None):
    p, db = _db()
    if idempotency_key and idempotency_key in db["keys"]:
        return db["keys"][idempotency_key]
    db["n"] += 1; cid = f"ch_{db['n']}"
    if idempotency_key: db["keys"][idempotency_key] = cid
    json.dump(db, open(p, "w")); return cid
