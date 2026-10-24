"""REL-02 / SEC-06: after a point-in-time restore, documents removed AFTER the restore point are back in the database
(their row says READY) although the purge job already deleted their file. This re-applies those removals.

Input: the `document_purged` events the worker logged since the restore point (Loki keeps logs 30 days):
    {service="worker"} |= "document_purged" | json | line_format "{{.document_id}}"
saved one id per line, e.g. purged_ids.txt.

    DATABASE_URL=postgresql+asyncpg://… python infra/backup/reapply_removals.py purged_ids.txt
"""

from __future__ import annotations

import asyncio
import os
import sys
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main(path: str) -> int:
    ids = [UUID(line.strip()) for line in open(path, encoding="utf-8") if line.strip()]
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as c:
        res = await c.execute(
            text("""
            UPDATE documents.document
               SET status = 'REMOVED', removed_at = COALESCE(removed_at, now()), purged_at = COALESCE(purged_at, now())
             WHERE id = ANY(:ids)"""),
            {"ids": ids},
        )
        await c.execute(text("DELETE FROM documents.text_chunk WHERE document_id = ANY(:ids)"), {"ids": ids})
        await c.execute(text("DELETE FROM documents.document_page WHERE document_id = ANY(:ids)"), {"ids": ids})
    await engine.dispose()
    print(f"{res.rowcount} documents marked removed and purged again ({len(ids)} ids in the file)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1])))
