"""
Lightweight SQLite-backed progress tracker so the crawl can be
stopped and resumed without redoing already-visited pages.
"""
import sqlite3
import json
from contextlib import closing


class ProgressStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pages (
                    url TEXT PRIMARY KEY,
                    status TEXT NOT NULL,       -- 'queued' | 'done' | 'failed'
                    title TEXT,
                    extracted_json TEXT,
                    screenshot_path TEXT,
                    summary TEXT
                )
                """
            )
            conn.commit()

    def is_visited(self, url: str) -> bool:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT status FROM pages WHERE url = ? AND status = 'done'", (url,)
            ).fetchone()
            return row is not None

    def mark_queued(self, url: str):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO pages (url, status) VALUES (?, 'queued')",
                (url,),
            )
            conn.commit()

    def mark_done(self, url: str, title: str, extracted: dict,
                   screenshot_path: str, summary: str):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO pages (url, status, title, extracted_json, screenshot_path, summary)
                VALUES (?, 'done', ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    status='done', title=excluded.title,
                    extracted_json=excluded.extracted_json,
                    screenshot_path=excluded.screenshot_path,
                    summary=excluded.summary
                """,
                (url, title, json.dumps(extracted), screenshot_path, summary),
            )
            conn.commit()

    def mark_failed(self, url: str):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO pages (url, status) VALUES (?, 'failed')
                ON CONFLICT(url) DO UPDATE SET status='failed'
                """,
                (url,),
            )
            conn.commit()

    def all_done_pages(self):
        """Returns list of dicts for pages successfully processed, in insertion order."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM pages WHERE status = 'done' ORDER BY rowid ASC"
            ).fetchall()
            result = []
            for r in rows:
                result.append({
                    "url": r["url"],
                    "title": r["title"],
                    "extracted": json.loads(r["extracted_json"]) if r["extracted_json"] else {},
                    "screenshot_path": r["screenshot_path"],
                    "summary": r["summary"],
                })
            return result