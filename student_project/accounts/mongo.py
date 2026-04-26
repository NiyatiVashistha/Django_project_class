from datetime import datetime
from django.conf import settings

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

_client = None


def get_db():
    """
    Returns the MongoDB database handle.
    Uses a 3-second timeout so the server doesn't hang if MongoDB is offline.
    Returns None if MongoDB is unavailable or pymongo is not installed.
    """
    global _client

    if not MONGO_AVAILABLE:
        return None

    if _client is None:
        try:
            _client = MongoClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=3000,   # fail fast: 3s
                connectTimeoutMS=3000,
                socketTimeoutMS=3000,
            )
            # Trigger a real connection test so we know it works NOW
            _client.admin.command("ping")
        except Exception:
            _client = None
            return None

    return _client[settings.MONGO_DB_NAME]


def _safe_insert(collection_name, doc):
    """Helper: insert a document or silently fail if MongoDB is down."""
    try:
        db = get_db()
        if db is None:
            return
        db[collection_name].insert_one(doc)
    except Exception:
        pass


def log_login(user_id):
    _safe_insert("logins", {"user_id": user_id, "timestamp": datetime.utcnow()})


def log_search(user_id, query, result_count):
    _safe_insert("search_logs", {
        "user_id": user_id,
        "query": query,
        "result_count": result_count,
        "timestamp": datetime.utcnow(),
    })


def log_payment(user_id, course_id, amount, status):
    _safe_insert("payments", {
        "user_id": user_id,
        "course_id": course_id,
        "amount": amount,
        "status": status,
        "timestamp": datetime.utcnow(),
    })


def log_activity(user_id, path, meta=None):
    _safe_insert("activities", {
        "user_id": user_id,
        "path": path,
        "meta": meta or {},
        "timestamp": datetime.utcnow(),
    })