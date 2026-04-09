import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from services.rag_service import get_answer, stream_answer

router = APIRouter()

# Request schema
class ChatMessage(BaseModel):
    role: str        # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []

# Endpoints
@router.post("/{bot_id}")
async def chat(bot_id: str, request: ChatRequest):
    """Return a single, complete answer for the given question."""
    result = get_answer(
        bot_id=bot_id,
        question=request.question,
        history=request.history or [],
    )
    return {
        "answer": result["answer"],
        "images": result["images"],
        "bot_id": bot_id,
    }


@router.get("/{bot_id}/stream")
async def chat_stream(bot_id: str, question: str):
    """Stream the answer back as Server-Sent Events (SSE).

    Text chunks are emitted as plain data events.
    After all text, a final images event is emitted:
      data: {"type": "images", "images": ["https://..."]}

    Note: History is not supported on the GET stream endpoint.
    Use the POST endpoint if you need history + streaming together.
    """

    def event_generator():
        for chunk in stream_answer(bot_id=bot_id, question=question, history=[]):
            # The image sentinel is a NUL-prefixed JSON string produced by stream_answer
            if chunk.startswith("\x00"):
                # This is the images payload — emit as a typed SSE event
                images_json = chunk[1:]  # strip the sentinel byte
                yield f"data: {images_json}\n\n"
            else:
                yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")