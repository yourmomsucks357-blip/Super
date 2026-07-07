import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from .models import MemoryItem

DB_PATH = Path("data/memory.db")

async def init_db():
    """Initialize database and create tables securely."""
    Path("data").mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory_items (
                item_id TEXT PRIMARY KEY,
                tier INTEGER NOT NULL DEFAULT 5,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                confidence REAL NOT NULL,
                usage_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tags ON memory_items(tags)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tier ON memory_items(tier)")
        await db.commit()

class DatabaseMemoryStore:
    def __init__(self):
        self.db_path = DB_PATH

    async def add(self, item: MemoryItem) -> MemoryItem:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO memory_items
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.item_id,
                item.tier.value if hasattr(item.tier, 'value') else (getattr(item, 'tier', 5) if hasattr(item, 'tier') else 5),
                item.title,
                item.content,
                ",".join(item.tags),
                item.confidence,
                item.usage_count,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
                str(item.metadata)
            ))
            await db.commit()
        return item

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM memory_items WHERE item_id = ?", (item_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_item(row)
        return None

    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM memory_items
                WHERE tags LIKE ? OR content LIKE ?
                ORDER BY tier DESC, usage_count DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_item(row) for row in rows]

    def _row_to_item(self, row) -> MemoryItem:
        return MemoryItem(
            item_id=row[0],
            tier=row[1],
            title=row[2],
            content=row[3],
            tags=row[4].split(",") if row[4] else [],
            confidence=row[5],
            usage_count=row[6],
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
            metadata=eval(row[9]) if row[9] else {}
        )