import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.scraper_firecrawl import (
    scrape_url,
    scrape_website,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_faq,
    _match_images_to_chunk,
)
from services.chunker import chunk_text
from services.embedder import embed_texts
from services.qdrant_service import create_collection, upsert_chunks, delete_collection

router = APIRouter()


# ── Request schemas ───────────────────────────────────────────────────────────

class URLTrainRequest(BaseModel):
    bot_id: str
    url: str


class FAQItem(BaseModel):
    question: str
    answer: str


class FAQTrainRequest(BaseModel):
    bot_id: str
    faqs: list[FAQItem]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _process_and_store(bot_id, raw_text=None, chunks=None, image_map=None, keyword_index=None):
    """Chunk → embed → store pipeline. Can accept raw text or pre-generated chunks."""
    if chunks is None:
        if raw_text is None:
            return 0
        chunks = chunk_text(raw_text)

    if not chunks:
        return 0

    # Match image URLs to chunks using 3-pass matching strategy
    image_map = image_map or {}
    keyword_index = keyword_index or {}
    images_list = [
        _match_images_to_chunk(chunk, image_map, keyword_index)
        for chunk in chunks
    ]

    vectors = embed_texts(chunks)
    create_collection(bot_id)
    upsert_chunks(bot_id=bot_id, chunks=chunks, embeddings=vectors, images_list=images_list)
    return len(chunks)


# ── Streaming URL train endpoint ──────────────────────────────────────────────

@router.post("/url/stream")
async def train_url_stream(request: URLTrainRequest):
    """
    SSE endpoint — streams real progress events while training.
    Frontend listens with fetch + ReadableStream.
    
    Events shape: {"percent": int, "message": str, "done"?: bool, "error"?: str, "chunks_stored"?: int}
    """
    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()

        def emit(percent: int, message: str, **extras):
            payload = {"percent": percent, "message": message, **extras}
            queue.put_nowait(payload)

        async def run_training():
            try:
                # ── Stage 1-4: Scraping (0% → 73%) ──────────────────────────
                # scrape_website returns (content, (image_map, keyword_index))
                raw_text, (image_map, keyword_index) = await scrape_website(request.url, on_progress=emit)

                # ── Stage 5: Chunking (75% → 80%) ────────────────────────────
                emit(75, "Chunking content...")
                await asyncio.to_thread(lambda: None)  # yield to event loop
                chunks = await asyncio.to_thread(chunk_text, raw_text)
                emit(80, f"Embedding {len(chunks)} chunks...")

                # ── Stage 6: Embedding (80% → 90%) ───────────────────────────
                vectors = await asyncio.to_thread(embed_texts, chunks)
                emit(90, "Saving to knowledge base...")

                # ── Stage 7: Qdrant store (90% → 100%) ───────────────────────
                await asyncio.to_thread(create_collection, request.bot_id)

                # Build per-chunk image lists using 3-pass matching
                images_list = [
                    _match_images_to_chunk(chunk, image_map, keyword_index)
                    for chunk in chunks
                ]

                await asyncio.to_thread(
                    upsert_chunks,
                    bot_id=request.bot_id,
                    chunks=chunks,
                    embeddings=vectors,
                    images_list=images_list,
                )
                emit(100, "Training complete!", done=True, chunks_stored=len(chunks))

            except ValueError as e:
                queue.put_nowait({"percent": 0, "message": str(e), "error": str(e), "done": True})
            except Exception as e:
                queue.put_nowait({"percent": 0, "message": f"Unexpected error: {e}", "error": str(e), "done": True})

        # Fire training as a background task
        asyncio.create_task(run_training())

        # Stream events until done
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield "data: " + json.dumps({"error": "Training timed out", "done": True}) + "\n\n"
                break

            yield "data: " + json.dumps(event) + "\n\n"

            if event.get("done"):
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Original non-streaming URL endpoint (kept for backward compat) ────────────

@router.post("/url")
async def train_from_url(request: URLTrainRequest):
    """Scrape a URL and ingest its content into Qdrant. Non-streaming fallback."""
    try:
        raw_text, (image_map, keyword_index) = await scrape_website(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chunks_stored = _process_and_store(request.bot_id, raw_text, image_map=image_map, keyword_index=keyword_index)
    return {"status": "success", "chunks_stored": chunks_stored}


# ── File upload endpoint ──────────────────────────────────────────────────────

@router.post("/file")
async def train_from_file(
    bot_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Accept a PDF or DOCX file and ingest its content into Qdrant."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    contents = await file.read()

    if ext == "pdf":
        raw_text = extract_text_from_pdf(contents)
    elif ext == "docx":
        raw_text = extract_text_from_docx(contents)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Only .pdf and .docx are accepted.",
        )

    chunks_stored = _process_and_store(bot_id, raw_text)
    return {"status": "success", "chunks_stored": chunks_stored}


# ── FAQ endpoint ──────────────────────────────────────────────────────────────

@router.post("/faq")
async def train_from_faq(request: FAQTrainRequest):
    """Convert a FAQ list to text and ingest it into Qdrant."""
    chunks = [f"Q: {faq.question}\nA: {faq.answer}" for faq in request.faqs]
    chunks_stored = _process_and_store(request.bot_id, chunks=chunks)
    return {"status": "success", "chunks_stored": chunks_stored}


# ── Delete endpoint ───────────────────────────────────────────────────────────

@router.delete("/{bot_id}")
async def clear_bot_training_data(bot_id: str):
    """Delete all training data (Qdrant collection) for the given bot."""
    try:
        delete_collection(bot_id)
        return {"status": "success", "message": "Training data cleared"}
    except Exception as e:
        return {"status": "success", "message": f"Data already clear or error: {str(e)}"}