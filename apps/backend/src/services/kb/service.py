from __future__ import annotations

from typing import Any

from src.db.sql.service import postgres_service


class KnowledgeBaseService:
    """Simple KB service backed by PostgreSQL tables.

    - Worldview entries: `worldview_entries`
    - Characters: `characters`

    All methods are best-effort: they catch errors and return empty results
    instead of raising, to avoid breaking generation flows in non-provisioned
    environments.
    """

    @staticmethod
    async def search_worldview(keyword: str, limit: int = 3) -> dict[str, Any]:
        like = f"%{keyword}%"
        try:
            rows = await postgres_service.execute(
                (
                    "SELECT id, name, entry_type::text AS entry_type, description, tags "
                    "FROM worldview_entries "
                    "WHERE name ILIKE $1 OR description ILIKE $1 "
                    "ORDER BY updated_at DESC LIMIT $2"
                ),
                (like, limit),
            )
        except Exception:
            rows = []

        items = []
        for r in rows or []:
            desc = r.get("description") or ""
            items.append(
                {
                    "id": str(r.get("id")),
                    "name": r.get("name"),
                    "type": r.get("entry_type"),
                    "snippet": desc[:200],
                    "tags": r.get("tags") or [],
                }
            )
        return {"query": keyword, "items": items}

    @staticmethod
    async def get_character_profile(name: str | None = None, character_id: str | None = None) -> dict[str, Any]:
        try:
            if character_id:
                rows = await postgres_service.execute(
                    (
                        "SELECT id, name, role, description, background_story, personality_traits, goals "
                        "FROM characters WHERE id::text = $1 LIMIT 1"
                    ),
                    (character_id,),
                )
            elif name:
                rows = await postgres_service.execute(
                    (
                        "SELECT id, name, role, description, background_story, personality_traits, goals "
                        "FROM characters WHERE name ILIKE $1 ORDER BY updated_at DESC LIMIT 1"
                    ),
                    (name,),
                )
            else:
                rows = []
        except Exception:
            rows = []

        if not rows:
            return {"found": False, "reason": "not_found"}

        r = rows[0]
        return {
            "found": True,
            "id": str(r.get("id")),
            "name": r.get("name"),
            "role": r.get("role"),
            "traits": r.get("personality_traits") or [],
            "goals": r.get("goals") or [],
            "background": r.get("background_story") or "",
            "description": r.get("description") or "",
        }

    @staticmethod
    async def get_glossary(keyword: str, limit: int = 5) -> dict[str, Any]:
        like = f"%{keyword}%"
        try:
            rows = await postgres_service.execute(
                (
                    "SELECT id, name, description "
                    "FROM worldview_entries "
                    "WHERE (name ILIKE $1 OR description ILIKE $1) "
                    "AND entry_type IN ('CONCEPT','OTHER') "
                    "ORDER BY updated_at DESC LIMIT $2"
                ),
                (like, limit),
            )
        except Exception:
            rows = []

        terms = []
        for r in rows or []:
            terms.append(
                {
                    "id": str(r.get("id")),
                    "term": r.get("name"),
                    "definition": (r.get("description") or "")[:200],
                }
            )
        return {"query": keyword, "terms": terms}
