from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.rag_service import get_answer, stream_answer

router = APIRouter()

# Request schema

class ChatRequest(BaseModel):
    question: str


# Endpoints

@router.post("/{bot_id}")
async def chat(bot_id: str, request: ChatRequest):
    """Return a single, complete answer for the given question."""
    answer = get_answer(bot_id=bot_id, question=request.question)
    return {"answer": answer, "bot_id": bot_id}


@router.get("/{bot_id}/stream")
async def chat_stream(bot_id: str, question: str):
    """Stream the answer back as Server-Sent Events (SSE)."""

    def event_generator():
        for chunk in stream_answer(bot_id=bot_id, question=question):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
