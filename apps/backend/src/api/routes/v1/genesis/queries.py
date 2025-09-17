"""Database query helpers for Genesis stage endpoints."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.novel.dialogue import ConversationRoundResponse


async def fetch_stage_conversation_rounds(
    db: AsyncSession,
    stage_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ConversationRoundResponse]:
    """
    Fetch all conversation rounds for a specific Genesis stage.

    Executes the SQL query from design document:
    SELECT r.* FROM genesis_stage_sessions gss
    JOIN conversation_rounds r ON r.session_id=gss.session_id
    WHERE gss.stage_id=$1 ORDER BY r.created_at;
    """
    query = text("""
        SELECT
            r.session_id,
            r.round_path,
            r.role,
            r.input,
            r.output,
            r.tool_calls,
            r.model,
            r.tokens_in,
            r.tokens_out,
            r.latency_ms,
            r.cost,
            r.correlation_id,
            r.created_at
        FROM genesis_stage_sessions gss
        JOIN conversation_rounds r ON r.session_id = gss.session_id
        WHERE gss.stage_id = :stage_id
        ORDER BY r.created_at
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(query, {"stage_id": stage_id, "limit": limit, "offset": offset})

    # Convert result to list of ConversationRoundResponse objects
    rounds = []
    for row in result:
        round_response = ConversationRoundResponse(
            session_id=row.session_id,
            round_path=row.round_path,
            role=row.role,
            input=row.input or {},
            output=row.output,
            tool_calls=row.tool_calls,
            model=row.model or "unknown",
            tokens_in=row.tokens_in,
            tokens_out=row.tokens_out,
            latency_ms=row.latency_ms,
            cost=row.cost,
            correlation_id=row.correlation_id,
            created_at=row.created_at,
        )
        rounds.append(round_response)

    return rounds
