import os
from dotenv import load_dotenv
from google import genai

from services.embedder import embed_single
from services.qdrant_service import search_similar

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)


SMALL_TALK = [
    "hi", "hello", "hey", "hii", "helo",
    "good morning", "good evening", "good afternoon", "good night",
    "bye", "goodbye", "see you", "take care",
    "thanks", "thank you", "thx",
    "how are you", "how r u", "whats up", "what's up",
    "what can you help me with", "what can you do"
]


def _check_small_talk(question: str) -> str | None:
    """Strictly matches a limited set of common phrases to keep RAG focused on content."""
    q = question.lower().strip().replace("?", "").replace("!", "")
    
    # Catch specific bot capability questions that should have a built-in response
    if q in ["what can you help me with", "what can you do"]:
        return "I can answer questions based on the content I've been trained on — including website pages, documents, and FAQs. Just ask me anything!"

    # 1. Any informational intent or longer queries immediately bypass small talk
    exclude_patterns = ["what is", "what are", "what can", "how do", "tell me", "explain"]
    
    # Exception: "what can" was in exclude_patterns but we already handled it above for exact matches.
    # For any OTHER "what can...", we still want to skip small talk.
    
    if any(p in q for p in exclude_patterns) or len(q) > 25: # Increased length to 25 to accommodate the phrases
        return None
    
    # 2. Match only if the entire message is in the vetted SMALL_TALK list
    if q in SMALL_TALK:
        if any(p in q for p in ["hi", "hello", "hey", "hii", "helo", "morning", "evening", "afternoon", "night"]):
            return "Hello! 👋 I'm here to help. Feel free to ask me anything about the content I've been trained on!"
        if any(p in q for p in ["thanks", "thank you", "thx"]):
            return "You're welcome! Feel free to ask if you have more questions. 😊"
        if any(p in q for p in ["bye", "goodbye", "see you", "take care"]):
            return "Goodbye! Have a great day! 👋"
        if any(p in q for p in ["how are you", "how r u", "whats up"]):
            return "I'm doing great, thank you for asking! How can I help you today?"
            
    return None


def _build_prompt(chunks: list[str], question: str) -> str:
    context = "\n\n---\n\n".join(chunks)
    return (
        "You are a helpful and professional AI assistant. Answer the user's question based ONLY on the provided context.\n"
        "Instructions:\n"
        "1. Use the context below to provide a detailed and accurate answer.\n"
        "2. If the answer is not contained within the context, politely state: \"I don't have information about that in my training data.\"\n"
        "3. Handle abbreviations (like 'ML' for 'Machine Learning') by finding relevant concepts in the context.\n"
        "4. Do not supplement information with outside knowledge.\n\n"
        "Context Content:\n"
        f"{context}\n\n"
        f"User Question: {question}\n\n"
        "Final Answer:"
    )


def get_answer(bot_id: str, question: str) -> str:
    """Embed the question, retrieve relevant chunks, and return a Gemini-generated answer."""
    # First, check for small talk
    small_talk_response = _check_small_talk(question)
    if small_talk_response:
        return small_talk_response

    vector = embed_single(question)
    chunks = search_similar(bot_id=bot_id, query_embedding=vector, top_k=10)

    if not chunks:
        return "I don't have enough information to answer that question."

    prompt = _build_prompt(chunks, question)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


def stream_answer(bot_id: str, question: str):
    """Same as get_answer but streams the response token by token."""
    # First, check for small talk
    small_talk_response = _check_small_talk(question)
    if small_talk_response:
        yield small_talk_response
        return

    vector = embed_single(question)
    chunks = search_similar(bot_id=bot_id, query_embedding=vector, top_k=10)

    if not chunks:
        yield "I don't have enough information to answer that question."
        return

    prompt = _build_prompt(chunks, question)
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"stream": True}
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text
