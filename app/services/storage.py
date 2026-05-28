"""طبقة التخزين - SQLite سريع"""
import sqlite3
import json
import time
import pickle
import zlib
from pathlib import Path
from app.config import DB_PATH, SESSION_TTL, UPLOADS_DIR


class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                data BLOB,
                created REAL
            )
        """)
        conn.commit()
        conn.close()

    def save(self, sid: str, data: dict) -> None:
        compressed = zlib.compress(pickle.dumps(data))
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?)",
            (sid, compressed, time.time())
        )
        conn.commit()
        conn.close()

    def get(self, sid: str) -> dict | None:
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT data, created FROM sessions WHERE id=?",
            (sid,)
        ).fetchone()
        conn.close()

        if row:
            data, created = row
            if time.time() - created < SESSION_TTL:
                return pickle.loads(zlib.decompress(data))
        return None


    def cleanup(self) -> int:
        """حذف الجلسات المنتهية ومجلداتها"""
        import shutil
        conn = sqlite3.connect(str(self.db_path))
        cutoff = time.time() - SESSION_TTL
        
        # حذف مجلدات uploads أولاً
        rows = conn.execute("SELECT id FROM sessions WHERE created < ?", (cutoff,)).fetchall()
        for (sid,) in rows:
            upload_path = UPLOADS_DIR / sid
            if upload_path.exists():
                shutil.rmtree(upload_path, ignore_errors=True)
        
        # حذف الجلسات من القاعدة
        cursor = conn.execute("DELETE FROM sessions WHERE created < ?", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
