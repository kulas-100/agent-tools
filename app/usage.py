"""
SQLite-based usage tracking and database management.
"""
import os
import aiosqlite
from contextlib import asynccontextmanager
from datetime import date

DB_PATH = os.getenv("DB_PATH", "agent_api.db")

TIER_LIMITS = {
    "free": 100,
    "pro": 10000,
    "enterprise": 1_000_000,
}


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    """Initialize database schema and seed default API key."""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash    TEXT    UNIQUE NOT NULL,
                name        TEXT,
                tier        TEXT    DEFAULT 'free',
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id     INTEGER NOT NULL,
                endpoint   TEXT,
                date       TEXT    DEFAULT (date('now')),
                called_at  TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY(key_id) REFERENCES api_keys(id)
            )
        """)

        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_key_date ON usage_logs(key_id, date)"
        )

        await db.commit()

        # Seed a default test key if none exist
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM api_keys")
        row = await cursor.fetchone()
        if row["cnt"] == 0:
            import hashlib
            default_key = os.getenv("DEFAULT_API_KEY", "test-api-key-12345")
            key_hash = hashlib.sha256(default_key.encode()).hexdigest()
            await db.execute(
                "INSERT INTO api_keys (key_hash, name, tier) VALUES (?, ?, ?)",
                (key_hash, "Default Test Key", "pro"),
            )
            await db.commit()
            print(f"\n{'='*50}")
            print(f"  Default API Key created: {default_key}")
            print(f"  Tier: pro (10,000 calls/day)")
            print(f"  Use header: X-API-Key: {default_key}")
            print(f"{'='*50}\n")


async def record_call(key_id: int, endpoint: str):
    """Record a single API call for a given key."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO usage_logs (key_id, endpoint, date) VALUES (?, ?, ?)",
            (key_id, endpoint, str(date.today())),
        )
        await db.commit()


async def get_usage(key_id: int) -> dict:
    """Return total and daily call counts for a key."""
    today = str(date.today())
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE key_id = ?",
            (key_id,),
        )
        total = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE key_id = ? AND date = ?",
            (key_id, today),
        )
        daily = (await cursor.fetchone())["cnt"]

    return {"total_calls": total, "daily_calls": daily}
