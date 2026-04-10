import os
from dotenv import load_dotenv
from typing import List
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

# Phrases that indicate the user is referring to something mentioned earlier
# rather than asking a self-contained question
VAGUE_TRIGGERS = [
    "tell me about it",
    "tell me about that",
    "tell me more about it",
    "tell me more about that",
    "tell me more",
    "more about it",
    "more about that",
    "more info",
    "more info on it",
    "more details",
    "more details on it",
    "why choose it",
    "why choose that",
    "why choose",
    "why should i choose it",
    "why should i use it",
    "what about it",
    "what is it",
    "explain it",
    "explain that",
    "explain more",
    "tell me everything about it",
    "what does it offer",
    "what does it include",
    "how does it work",
    "what are its features",
    "and it",
    "that design",
    "that service",
    "this service",
    "that product",
    "this product",
    "that feature",
    "this feature",
]


def _is_low_confidence_answer(answer: str) -> bool:
    """Return True when the model's answer signals it doesn't have the information."""
    low = answer.lower()
    return any(phrase in low for phrase in [
        "i don't have that information",
        "i don't have information",
        "i don't know",
        "no information",
        "cannot find",
        "not sure",
        "unable to find",
        "please contact us",
        "contact us directly",
    ])


def _is_vague(text: str) -> bool:
    """Check if a message is a vague follow-up that needs context resolution."""
    q = text.lower().strip().replace("?", "").replace("!", "").strip()
    return any(trigger in q for trigger in VAGUE_TRIGGERS)


def _extract_topic_from_text(text: str) -> str | None:
    """
    Extract the most likely topic noun phrase from a message.
    Strips filler phrases to get the core subject.
    Works on both user questions and assistant answers.
    """
    strip_prefixes = [
        "yes, we offer",
        "yes, we do offer",
        "yes, we provide",
        "we offer",
        "we provide",
        "we do offer",
        "sure, we offer",
        "absolutely, we offer",
        "of course, we offer",
        "yes we offer",
        "yes we do offer",
        "do you offer",
        "do you provide",
        "tell me about",
        "what is",
        "what are",
        "i want to know about",
        "can you tell me about",
    ]

    t = text.lower().strip().rstrip("?.!")
    for prefix in strip_prefixes:
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
            break

    # Remove trailing filler
    strip_suffixes = [
        "service",
        "services",
        "please",
        "for me",
    ]
    for suffix in strip_suffixes:
        if t.endswith(suffix):
            t = t[: -len(suffix)].strip()

    t = t.strip(" .,;:-")
    return t if len(t) > 2 else None


def _resolve_question_with_history(question: str, history: list) -> str:
    """
    If the current question is vague (e.g. 'tell me about it', 'why choose it?'),
    find the most recent topic from history — checking both user and assistant
    messages — and append it so the embedder has something meaningful to search.

    Priority order:
    1. Last non-vague USER message (most direct signal)
    2. Last ASSISTANT message (catches cases where topic came from bot's reply)
    """
    if not _is_vague(question):
        return question

    if not history:
        return question

    # Pass 1 — scan user messages newest-first for a non-vague anchor
    for msg in reversed(history):
        if msg.role == "user" and not _is_vague(msg.content):
            topic = _extract_topic_from_text(msg.content)
            if topic:
                return f"{question} {topic}"

    # Pass 2 — fall back to last assistant message for topic extraction
    for msg in reversed(history):
        if msg.role == "assistant":
            topic = _extract_topic_from_text(msg.content)
            if topic:
                return f"{question} {topic}"

    return question


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


def _build_prompt(chunks, question, history, has_images=False):
    """Build the Gemini prompt including RAG context and conversation history."""
    context = "\n\n---\n\n".join(chunks)

    # Format last 6 turns of history (3 exchanges) to keep prompt size bounded
    history_text = ""
    if history:
        recent = history[-6:]
        lines = []
        for msg in recent:
            role_label = "Customer" if msg.role == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.content}")
        history_text = "\n".join(lines)

    history_section = (
        f"Conversation so far:\n{history_text}\n\n"
        if history_text
        else ""
    )

    image_note = (
        "10. Relevant product images will be shown to the user automatically below your answer. "
        "Do not describe, reference, or mention the images in your text response.\n"
        if has_images else ""
    )

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
        "8. Handle abbreviations like 'ML' for 'Machine Learning' by finding relevant concepts in the context.\n"
        "9. Use the conversation history to understand follow-up questions and references like "
        "'it', 'that', 'this service', 'tell me more' — resolve them from prior turns.\n"
        f"{image_note}"
        "\n"
        f"{history_section}"
        f"Context:\n{context}\n\n"
        f"Customer question: {question}\n\n"
        "Your response:"
    )


def get_answer(bot_id, question, history=[]):
    """Embed the question, retrieve relevant chunks, and return a Gemini-generated answer."""
    small_talk_response = _check_small_talk(question)
    if small_talk_response:
        return {"answer": small_talk_response, "images": []}

    # Resolve vague follow-ups before expanding/embedding
    resolved_question = _resolve_question_with_history(question, history)
    expanded = _expand_query(resolved_question)

    vector = embed_single(expanded)
    hits = search_similar(bot_id=bot_id, query_embedding=vector, top_k=20)

    if not hits:
        return {"answer": "I don't have enough information to answer that question.", "images": []}

    # Extract texts and collect images from chunk payloads
    chunks = [hit.payload.get("text", "") for hit in hits]
    all_images = []
    for hit in hits:
        all_images.extend(hit.payload.get("images", []))
    # Deduplicate while preserving order, cap at 4
    seen = set()
    unique_images = []
    for img in all_images:
        url = img.get("url", "") if isinstance(img, dict) else img
        if url and url not in seen:
            seen.add(url)
            unique_images.append(img)
    unique_images = unique_images[:4]

    prompt = _build_prompt(chunks, question, history, has_images=bool(unique_images))
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    if _is_low_confidence_answer(response.text):
        return {"answer": response.text, "images": []}
    return {"answer": response.text, "images": unique_images}


def stream_answer(bot_id, question, history=[]):
    """Same as get_answer but streams the response token by token.
    
    Yields text chunks during streaming, then a final JSON event with images.
    """
    import json as _json
    small_talk_response = _check_small_talk(question)
    if small_talk_response:
        yield small_talk_response
        return

    resolved_question = _resolve_question_with_history(question, history)
    expanded = _expand_query(resolved_question)

    vector = embed_single(expanded)
    hits = search_similar(bot_id=bot_id, query_embedding=vector, top_k=20)

    if not hits:
        yield "I don't have enough information to answer that question."
        return

    # Extract texts and collect images from chunk payloads
    chunks = [hit.payload.get("text", "") for hit in hits]
    all_images = []
    for hit in hits:
        all_images.extend(hit.payload.get("images", []))
    seen = set()
    unique_images = []
    for img in all_images:
        url = img.get("url", "") if isinstance(img, dict) else img
        if url and url not in seen:
            seen.add(url)
            unique_images.append(img)
    unique_images = unique_images[:4]

    prompt = _build_prompt(chunks, question, history, has_images=bool(unique_images))

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt, config={"stream": True}
    )

    full_answer = ""
    for chunk in response:
        if chunk.text:
            full_answer += chunk.text
            yield chunk.text

    # Final event — images (suppressed when confidence is low)
    if _is_low_confidence_answer(full_answer):
        yield "\x00" + _json.dumps({"type": "images", "images": []})
    else:
        yield "\x00" + _json.dumps({"type": "images", "images": unique_images})