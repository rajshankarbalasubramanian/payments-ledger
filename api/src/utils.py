# api/src/utils.py
import hashlib, json

def canonical_json(obj):
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)

def hash_body(body):
    return hashlib.sha256(canonical_json(body).encode()).hexdigest()
