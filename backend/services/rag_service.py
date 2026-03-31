import os
from dotenv import load_dotenv
from google import genai

from services.embedder import embed_single
from services.qdrant_service import search_similar

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)


SMALL_TALK = [
    "hi",
    "hello",
    "hey",
    "hii",
    "helo",
    "good morning",
    "good evening",
    "good afternoon",
    "good night",
    "bye",
    "goodbye",
    "see you",
    "take care",
    "thanks",
    "thank you",
    "thx",
    "how are you",
    "how r u",
    "whats up",
    "what's up",
    "what can you help me with",
    "what can you do",
]


def _check_small_talk(question: str) -> str | None:
    """Strictly matches a limited set of common phrases to keep RAG focused on content."""
    q = question.lower().strip().replace("?", "").replace("!", "")

    if q in ["what can you help me with", "what can you do"]:
        return "I can answer questions based on the content I've been trained on — including website pages, documents, and FAQs. Just ask me anything!"

    exclude_patterns = [
        "what is",
        "what are",
        "what can",
        "how do",
        "tell me",
        "explain",
    ]

    if any(p in q for p in exclude_patterns) or len(q) > 25:
        return None

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


def _expand_query(question: str) -> str:
    """
    Expand short or vague queries using only generic semantic synonyms.
    Never hardcode website-specific data here — this must work for any website.
    """
    q = question.lower().strip()

    expansions = {
        "email": "email address contact mail",
        "mail": "email address contact mail",
        "e-mail": "email address contact mail",
        "phone": "phone number mobile contact call whatsapp",
        "mobile": "mobile phone number contact call whatsapp",
        "number": "phone number mobile contact",
        "whatsapp": "whatsapp phone number contact",
        "contact": "contact email phone address location get in touch",
        "address": "address location office headquarters",
        "location": "location address office headquarters city",
        "office": "office location address headquarters",
        "pricing": "pricing cost price plans packages fees",
        "price": "pricing cost price plans packages fees",
        "cost": "pricing cost price plans packages fees",
        "career": "career jobs hiring recruitment hr human resources",
        "job": "career jobs hiring recruitment hr",
        "hiring": "career jobs hiring recruitment hr",
        "hr": "hr human resources career hiring",
        "about": "about us company overview mission vision who we are",
        "founder": "founder ceo owner team leadership",
        "team": "team members staff employees leadership",
        "hours": "working hours business hours open close timing",
        "timing": "working hours business hours open close timing",
        "refund": "refund return policy cancellation",
        "support": "support help customer service contact",
        "service": "services offerings products solutions",
        "product": "products services offerings solutions",
        "review": "reviews testimonials feedback ratings customers",
        "testimonial": "reviews testimonials feedback ratings customers",
        "social": "social media instagram facebook twitter linkedin",
        "instagram": "social media instagram contact follow",
        "facebook": "social media facebook contact follow",
        "linkedin": "social media linkedin contact follow",
        "twitter": "social media twitter contact follow",
        "faq": "faq frequently asked questions help",
        "shipping": "shipping delivery logistics dispatch",
        "delivery": "shipping delivery logistics dispatch",
        "return": "return refund policy exchange",
        "warranty": "warranty guarantee policy terms",
        "partner": "partners clients collaborations affiliates",
        "client": "clients customers partners case studies",
    }

    for key, expansion in expansions.items():
        if key in q:
            return f"{question} {expansion}"

    return question


def _build_prompt(chunks: list[str], question: str) -> str:
    context = "\n\n---\n\n".join(chunks)
    return (
        "You are a friendly and professional customer support assistant. "
        "Answer the user's question based ONLY on the provided context.\n\n"
        "STRICT FORMATTING RULES — follow these exactly:\n"
        "1. Write in plain, natural conversational sentences. No markdown whatsoever.\n"
        "2. Do NOT use **, *, #, bullet points, numbered lists, or any markdown symbols.\n"
        "3. If listing multiple items, write them as natural sentences: 'We offer X, Y, and Z.' "
        "or use a simple line break between items — never use * or - as bullet points.\n"
        "4. Keep answers concise and clear. Avoid over-explaining.\n"
        "5. Sound like a helpful human support agent, not a document or report.\n"
        "6. If the answer is not in the context, say exactly: "
        "'I don't have that information — please contact us directly for more details.'\n"
        "7. Do not use outside knowledge. Only use the context provided.\n"
        "8. Handle abbreviations like 'ML' for 'Machine Learning' by finding relevant concepts in the context.\n\n"
        "Context:\n"
        f"{context}\n\n"
        f"Customer question: {question}\n\n"
        "Your response:"
    )


def get_answer(bot_id: str, question: str) -> str:
    """Embed the question, retrieve relevant chunks, and return a Gemini-generated answer."""
    small_talk_response = _check_small_talk(question)
    if small_talk_response:
        return small_talk_response

    expanded = _expand_query(question)
    vector = embed_single(expanded)
    chunks = search_similar(bot_id=bot_id, query_embedding=vector, top_k=20)

    if not chunks:
        return "I don't have enough information to answer that question."

    prompt = _build_prompt(chunks, question)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text


def stream_answer(bot_id: str, question: str):
    """Same as get_answer but streams the response token by token."""
    small_talk_response = _check_small_talk(question)
    if small_talk_response:
        yield small_talk_response
        return

    expanded = _expand_query(question)
    vector = embed_single(expanded)
    chunks = search_similar(bot_id=bot_id, query_embedding=vector, top_k=20)

    if not chunks:
        yield "I don't have enough information to answer that question."
        return

    prompt = _build_prompt(chunks, question)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt, config={"stream": True}
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text