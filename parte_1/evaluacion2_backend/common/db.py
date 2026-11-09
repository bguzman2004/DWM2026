import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Database:
    def __init__(self, path):
        self.path = path
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @contextmanager
    def tx(self):
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()

    def all(self, sql, params=()):
        conn = self.connect()
        try:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def one(self, sql, params=()):
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def init(self, schema_path, seed=None):
        with open(schema_path, encoding="utf-8") as handle:
            script = handle.read()
        conn = self.connect()
        try:
            conn.executescript(script)
            conn.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            seeded = conn.execute("SELECT 1 FROM meta WHERE key='seeded'").fetchone()
        finally:
            conn.close()
        if seed and not seeded:
            with self.tx() as c:
                seed(c)
                c.execute("INSERT INTO meta(key,value) VALUES('seeded','1')")

    def ping(self):
        self.one("SELECT 1 AS ok")
