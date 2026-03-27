from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from services.scraper import scrape_url, extract_text_from_pdf, extract_text_from_docx, extract_text_from_faq
from services.chunker import chunk_text
from services.embedder import embed_texts
from services.qdrant_service import create_collection, upsert_chunks, delete_collection

router = APIRouter()


# Request schemas

class URLTrainRequest(BaseModel):
    bot_id: str
    url: str


class FAQItem(BaseModel):
    question: str
    answer: str


class FAQTrainRequest(BaseModel):
    bot_id: str
    faqs: list[FAQItem]


# Helpers

def _process_and_store(bot_id: str, raw_text: Optional[str] = None, chunks: Optional[List[str]] = None) -> int:
    """Chunk → embed → store pipeline. Can accept raw text or pre-generated chunks."""
    if chunks is None:
        if raw_text is None:
            return 0
        chunks = chunk_text(raw_text)
    
    if not chunks:
        return 0

    vectors = embed_texts(chunks)
    create_collection(bot_id)
    upsert_chunks(bot_id=bot_id, chunks=chunks, embeddings=vectors)
    return len(chunks)


# Endpoints

@router.post("/url")
async def train_from_url(request: URLTrainRequest):
    """Scrape a URL and ingest its content into Qdrant."""
    try:
        raw_text = await scrape_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chunks_stored = _process_and_store(request.bot_id, raw_text)
    return {"status": "success", "chunks_stored": chunks_stored}


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


@router.post("/faq")
async def train_from_faq(request: FAQTrainRequest):
    """Convert a FAQ list to text and ingest it into Qdrant."""
    # Instead of joining with \n\n and re-chunking/filtering,
    # we treat each FAQ as its own context-rich chunk to ensure
    # short entries (like "what is ai") are preserved and retrieved correctly.
    chunks = [f"Q: {faq.question}\nA: {faq.answer}" for faq in request.faqs]
    chunks_stored = _process_and_store(request.bot_id, chunks=chunks)
    return {"status": "success", "chunks_stored": chunks_stored}


@router.delete("/{bot_id}")
async def clear_bot_training_data(bot_id: str):
    """Delete all training data (Qdrant collection) for the given bot."""
    try:
        delete_collection(bot_id)
        return {"status": "success", "message": "Training data cleared"}
    except Exception as e:
        return {"status": "success", "message": f"Data already clear or error: {str(e)}"}
