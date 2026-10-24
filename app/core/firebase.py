import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings

_db = None

def init_firebase():
    global _db
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()  # Gunakan kredensial default
        firebase_admin.initialize_app(cred)
    if _db is None:
        _db = firestore.client()
    return _db

def get_db():
    return _db or init_firebase()
