"""Search feature codegen for NIKAME.

Provides full-text search capabilities.
"""

from __future__ import annotations
import logging
from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen

@register_codegen
class SearchCodegen(BaseCodegen):
    """Generates search functionality code."""

    NAME = "search"
    DESCRIPTION = "Full-text search (Postgres/Elasticsearch)"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        has_postgres = "postgres" in active_modules

        router_py = """\\"\\"\\"Search routing and logic.\\"\\"\\"
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from core.database import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

@router.get("/")
async def perform_search(query: str, db: AsyncSession = Depends(get_db)):
    \\"\\"\\"Perform full-text search.\\"\\"\\"
    # Example using Postgres raw full-text search
    stmt = text("SELECT id, title, body FROM search_documents WHERE document_fts @@ plainto_tsquery(:q)")
    result = await db.execute(stmt, {"q": query})
    return [{"id": r[0], "title": r[1]} for r in result.all()]
"""

        triggers_py = """\\"\\"\\"Auto-wired search triggers on Postgres models.\\"\\"\\"
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
import logging

logger = logging.getLogger(__name__)

async def wire_search_triggers(session: AsyncSession):
    \\"\\"\\"Automatically configures Postgres trigger for tsvector updates.\\"\\"\\"
    try:
        await session.execute(text('''
            CREATE OR REPLACE FUNCTION search_documents_trigger() RETURNS trigger AS $$
            begin
              new.document_fts :=
                 setweight(to_tsvector('pg_catalog.english', coalesce(new.title,'')), 'A') ||
                 setweight(to_tsvector('pg_catalog.english', coalesce(new.body,'')), 'B');
              return new;
            end
            $$ LANGUAGE plpgsql;
        '''))
        await session.execute(text('''
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tsvectorupdate') THEN
                    CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
                    ON search_documents FOR EACH ROW EXECUTE FUNCTION search_documents_trigger();
                END IF;
            END
            $$;
        '''))
        logger.info("Search triggers auto-wired on Postgres models.")
    except Exception as e:
        logger.error(f"Failed to wire search triggers: {e}")
""" if has_postgres else ""

        files = [
            ("app/api/search/router.py", router_py),
        ]
        
        if triggers_py:
            files.append(("app/api/search/triggers.py", triggers_py))
            
        return files
