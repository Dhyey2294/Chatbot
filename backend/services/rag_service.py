import os
import logging
from dotenv import load_dotenv
from typing import List
from google import genai

logger = logging.getLogger(__name__)

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
    return any(
        phrase in low
        for phrase in [
            "i don't have that information",
            "i don't have information",
            "i don't know",
            "no information available",
            "please contact us directly",
            "contact us directly for more details",
        ]
    )


def _is_vague(text: str) -> bool:
    """Check if a message is a vague follow-up that needs context resolution."""
    q = text.lower().strip().replace("?", "").replace("!", "").strip()
    return any(trigger in q for trigger in VAGUE_TRIGGERS)


_FOLLOWUP_DETAIL_PATTERNS = {
    "price",
    "cost",
    "how much",
    "available",
    "availability",
    "in stock",
    "size",
    "sizes",
    "colour",
    "color",
    "shipping",
    "delivery",
    "return",
    "refund",
    "material",
    "fabric",
    "care",
}


def _is_followup_detail_question(question: str, history: list) -> bool:
    """Return True if question is asking for a detail about a previously discussed product."""
    if not history:
        return False
    q = question.lower().strip()
    words = set(q.split())
    follow_up_signals = {"it", "its", "this", "that", "these", "those"}
    has_pronoun = bool(words & follow_up_signals)
    has_detail_word = any(p in q for p in _FOLLOWUP_DETAIL_PATTERNS)
    if not has_detail_word:
        return False
    # Either has pronoun, OR is a short query (≤6 words) that's just name + detail word
    return has_pronoun or len(words) <= 6


def _is_specific_product_query(question: str, history: list) -> bool:
    """
    Return True if the question is about a specific named product.
    Heuristic: specific product names tend to be long (5+ words after stripping prefixes),
    or the question references a previously discussed specific product via pronouns.
    """
    q = question.lower().strip()
    # Follow-up about previously discussed product
    follow_up_signals = {"it", "its", "this", "that"}
    if set(q.split()) & follow_up_signals and history:
        return True
    # Strip common question prefixes and check if remaining text is a long specific name
    for prefix in [
        "show me",
        "find me",
        "what is",
        "tell me about",
        "do you have",
        "can you show me",
    ]:
        if q.startswith(prefix):
            q = q[len(prefix) :].strip()
            break
    # Specific product names are typically 5+ words
    return len(q.split()) >= 5


_USELESS_TOPICS = {
    "something similar",
    "something",
    "similar",
    "same",
    "more",
    "it",
    "this",
    "that",
    "these",
    "those",
    "one",
    "ones",
}


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
        "can you show me",
        "show me",
        "show me something similar to",
        "something similar to",
        "find me",
        "do you have",
        "is it available",
        "is there",
    ]

    t = text.lower().strip().rstrip("?.!")
    for prefix in strip_prefixes:
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
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
    if len(t) <= 2 or t.lower() in _USELESS_TOPICS:
        return None
    return t


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


def _build_search_query(question: str, history: list) -> str:
    if not history:
        return question

    q_lower = question.lower()

    # If question contains follow-up pronouns, it needs history context
    follow_up_signals = {
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "similar",
        "same",
    }
    words = set(q_lower.split())

    # New topic question — don't pollute with old context
    if not words & follow_up_signals:
        return question

    # Follow-up question — append recent topic from history
    recent_topic = None
    for msg in reversed(history):
        if msg.role == "user":
            topic = _extract_topic_from_text(msg.content)
            if topic and len(topic) > 3:
                recent_topic = topic
                break
    if not recent_topic:
        for msg in reversed(history):
            if msg.role == "assistant":
                topic = _extract_topic_from_text(msg.content)
                if topic and len(topic) > 3:
                    recent_topic = topic
                    break

    if not recent_topic or recent_topic.lower() in q_lower:
        return question

    return f"{question} {recent_topic}"


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
        if any(
            p in q
            for p in [
                "hi",
                "hello",
                "hey",
                "hii",
                "helo",
                "morning",
                "evening",
                "afternoon",
                "night",
            ]
        ):
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

    extras = []
    for key, expansion in expansions.items():
        if key in q:
            extras.append(expansion)
    if extras:
        return f"{question} {' '.join(extras)}"

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
        f"Conversation so far:\n{history_text}\n\n" if history_text else ""
    )

    image_note = (
        "14. Relevant product images will be shown to the user automatically below your answer. "
        "Do not describe, reference, or mention the images in your text response.\n"
        if has_images
        else ""
    )

    return (
        "You are a customer support assistant. "
        "The context below contains real data from the website you represent. "
        "Your job is to find the most relevant items in the context and answer directly. "
        "You MUST attempt to answer using the context — never refuse if relevant data exists.\n\n"
        "RESPONSE FORMATTING RULES:\n"
        "1. CRITICAL: Every bullet point and every field MUST be on its own separate line. Never put two items or two fields on the same line.\n"
        "2. For a SPECIFIC PRODUCT query, respond in this EXACT format with each field on its own line:\n"
        "**Name:** [product name]\n"
        "**Price:** [price]\n"
        "**Color:** [color only, no size]\n"
        "**Sizes:** [sizes only, no color — just XS, S, M, L, XL etc]\n"
        "**Description:** [one sentence]\n"
        "Do not put multiple fields on the same line. Each field must start on a new line.\n"
        "3. For a PRODUCT category query (show me jeans, show me dresses), list EXACTLY 3 products in this format:\n"
        "• [Exact product name from context] — Rs. [exact price from context]\n"
        "Use the EXACT product name and price as they appear in the context. Do not paraphrase or shorten names.\n"
        "4. Always start your response with one short friendly sentence before any bullet list. Never start directly with a bullet point.\n"
        "5. For single fact answers (contact number, email, address), give one intro sentence then the fact. Example: 'You can reach us at +1 234 567 8900.'\n"
        "6. For SINGLE fact questions (what is your email, where are you located), answer in 1-2 plain sentences. No bullets.\n"
        "7. Never use **, #, numbered lists, or any other markdown. Only use • for bullets.\n"
        "8. Keep all answers concise. No unnecessary descriptions or filler sentences.\n"
        "9. NEVER refuse a category query. If the context has products of the requested type, list the 3 most relevant ones even if gender, color or other attributes are not an exact match. Always attempt to answer.\n"
        "10. Use conversation history to resolve 'it', 'this', 'that' — always refer back to the last discussed product or topic.\n"
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
    search_query = _build_search_query(question, history)
    expanded = _expand_query(search_query)

    vector = embed_single(expanded)
    hits = search_similar(bot_id=bot_id, query_embedding=vector, top_k=20)
    logger.info("RAG hits for '%s': %d chunks retrieved", question, len(hits))

    if not hits:
        return {
            "answer": "I don't have enough information to answer that question.",
            "images": [],
        }

    # Extract texts and collect images from chunk payloads
    chunks = [hit.payload.get("text", "") for hit in hits]
    is_specific = _is_specific_product_query(question, history)

    # For category queries, prefer product chunks over editorial/blog chunks
    if not is_specific:
        product_hits = [h for h in hits if "Price:" in h.payload.get("text", "") or "URL:" in h.payload.get("text", "")]
        other_hits = [h for h in hits if h not in product_hits]
        # Use product chunks first, fall back to others if not enough
        hits = (product_hits + other_hits)[:20]
        chunks = [hit.payload.get("text", "") for hit in hits]

    all_images = []
    if is_specific:
        # Resolve the actual product name being asked about
        product_query = question.lower().strip()
        for prefix in [
            "show me",
            "find me",
            "can you show me",
            "do you have",
            "what is",
            "tell me about",
            "price of",
        ]:
            if product_query.startswith(prefix):
                product_query = product_query[len(prefix) :].strip()
                break
        # If it's a pronoun-based follow-up, resolve from history
        if set(product_query.split()) & {"it", "its", "this", "that"} and history:
            for msg in reversed(history):
                if msg.role == "user":
                    candidate = msg.content.lower()
                    for prefix in [
                        "show me",
                        "find me",
                        "can you show me",
                        "do you have",
                    ]:
                        if candidate.startswith(prefix):
                            candidate = candidate[len(prefix) :].strip()
                            break
                    if len(candidate.split()) >= 3:
                        product_query = candidate
                        break
        # Only collect images from chunks whose text contains most product name words
        query_words = [w for w in product_query.split() if len(w) >= 2]
        scored_hits = []
        for hit in hits[:15]:
            text = hit.payload.get("text", "").lower()
            images = hit.payload.get("images", [])
            if not images:
                continue
            match_count = sum(1 for w in query_words if w in text)
            score = match_count / len(query_words) if query_words else 0
            if score >= 0.6:
                scored_hits.append((score, images))
        scored_hits.sort(key=lambda x: x[0], reverse=True)
        # Only take images from the single best matching chunk
        # It already has up to 3 images of the same product stored at training time
        if scored_hits:
            all_images.extend(scored_hits[0][1])
    else:
        # Category query: store hits for post-answer image matching
        pass  # images collected after answer generation for category queries

    seen = set()
    unique_images = []
    for img in all_images:
        url = img.get("url", "") if isinstance(img, dict) else img
        if url and url not in seen:
            seen.add(url)
            unique_images.append(img)

    # Cap: 3 for both specific product and category
    unique_images = unique_images[:3]

    # Suppress images for follow-up detail questions (price, size etc)
    if _is_followup_detail_question(question, history):
        unique_images = []

    prompt = _build_prompt(chunks, question, history, has_images=bool(unique_images))
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

    if not is_specific and not _is_followup_detail_question(question, history):
        # Match images by finding chunks whose first line (product name) appears in the answer
        answer_lower = response.text.lower()
        matched_products = []
        seen_names = set()

        for hit in hits:
            text = hit.payload.get("text", "").lower()
            chunk_imgs = hit.payload.get("images", [])
            if not chunk_imgs:
                continue
            # Get product name from first line of chunk
            first_line = text.split("\n")[0].strip()
            if not first_line or len(first_line) < 4:
                continue
            # Check if any significant word sequence from first line appears in answer
            name_words = [w for w in first_line.split() if len(w) >= 4]
            if not name_words:
                continue
            match_count = sum(1 for w in name_words if w in answer_lower)
            score = match_count / len(name_words)
            if score >= 0.4 and first_line not in seen_names:
                seen_names.add(first_line)
                matched_products.append((score, chunk_imgs))

        matched_products.sort(key=lambda x: x[0], reverse=True)
        all_images = []
        for _, imgs in matched_products[:3]:
            all_images.extend(imgs[:1])  # 1 image per product = 3 total

        seen = set()
        unique_images = []
        for img in all_images:
            url = img.get("url", "") if isinstance(img, dict) else img
            if url and url not in seen:
                seen.add(url)
                unique_images.append(img)
        unique_images = unique_images[:3]

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

    search_query = _build_search_query(question, history)
    expanded = _expand_query(search_query)

    vector = embed_single(expanded)
    hits = search_similar(bot_id=bot_id, query_embedding=vector, top_k=20)
    logger.info("RAG hits for '%s': %d chunks retrieved", question, len(hits))

    if not hits:
        yield "I don't have enough information to answer that question."
        return

    # Extract texts and collect images from chunk payloads
    chunks = [hit.payload.get("text", "") for hit in hits]
    is_specific = _is_specific_product_query(question, history)

    # For category queries, prefer product chunks over editorial/blog chunks
    if not is_specific:
        product_hits = [h for h in hits if "Price:" in h.payload.get("text", "") or "URL:" in h.payload.get("text", "")]
        other_hits = [h for h in hits if h not in product_hits]
        # Use product chunks first, fall back to others if not enough
        hits = (product_hits + other_hits)[:20]
        chunks = [hit.payload.get("text", "") for hit in hits]

    all_images = []
    if is_specific:
        # Resolve the actual product name being asked about
        product_query = question.lower().strip()
        for prefix in [
            "show me",
            "find me",
            "can you show me",
            "do you have",
            "what is",
            "tell me about",
            "price of",
        ]:
            if product_query.startswith(prefix):
                product_query = product_query[len(prefix) :].strip()
                break
        # If it's a pronoun-based follow-up, resolve from history
        if set(product_query.split()) & {"it", "its", "this", "that"} and history:
            for msg in reversed(history):
                if msg.role == "user":
                    candidate = msg.content.lower()
                    for prefix in [
                        "show me",
                        "find me",
                        "can you show me",
                        "do you have",
                    ]:
                        if candidate.startswith(prefix):
                            candidate = candidate[len(prefix) :].strip()
                            break
                    if len(candidate.split()) >= 3:
                        product_query = candidate
                        break
        # Only collect images from chunks whose text contains most product name words
        query_words = [w for w in product_query.split() if len(w) >= 2]
        scored_hits = []
        for hit in hits[:15]:
            text = hit.payload.get("text", "").lower()
            images = hit.payload.get("images", [])
            if not images:
                continue
            match_count = sum(1 for w in query_words if w in text)
            score = match_count / len(query_words) if query_words else 0
            if score >= 0.6:
                scored_hits.append((score, images))
        scored_hits.sort(key=lambda x: x[0], reverse=True)
        # Only take images from the single best matching chunk
        # It already has up to 3 images of the same product stored at training time
        if scored_hits:
            all_images.extend(scored_hits[0][1])
    else:
        # Category query: store hits for post-answer image matching
        pass  # images collected after answer generation for category queries

    seen = set()
    unique_images = []
    for img in all_images:
        url = img.get("url", "") if isinstance(img, dict) else img
        if url and url not in seen:
            seen.add(url)
            unique_images.append(img)

    # Cap: 3 for both specific product and category
    unique_images = unique_images[:3]

    # Suppress images for follow-up detail questions (price, size etc)
    if _is_followup_detail_question(question, history):
        unique_images = []

    prompt = _build_prompt(chunks, question, history, has_images=bool(unique_images))

    full_answer = ""
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-flash", contents=prompt
    ):
        if chunk.text:
            full_answer += chunk.text
            yield chunk.text

    if not is_specific and not _is_followup_detail_question(question, history):
        # Match images by finding chunks whose first line (product name) appears in the answer
        answer_lower = full_answer.lower()
        matched_products = []
        seen_names = set()

        for hit in hits:
            text = hit.payload.get("text", "").lower()
            chunk_imgs = hit.payload.get("images", [])
            if not chunk_imgs:
                continue
            # Get product name from first line of chunk
            first_line = text.split("\n")[0].strip()
            if not first_line or len(first_line) < 4:
                continue
            # Check if any significant word sequence from first line appears in answer
            name_words = [w for w in first_line.split() if len(w) >= 4]
            if not name_words:
                continue
            match_count = sum(1 for w in name_words if w in answer_lower)
            score = match_count / len(name_words)
            if score >= 0.4 and first_line not in seen_names:
                seen_names.add(first_line)
                matched_products.append((score, chunk_imgs))

        matched_products.sort(key=lambda x: x[0], reverse=True)
        all_images = []
        for _, imgs in matched_products[:3]:
            all_images.extend(imgs[:1])  # 1 image per product = 3 total

        seen = set()
        unique_images = []
        for img in all_images:
            url = img.get("url", "") if isinstance(img, dict) else img
            if url and url not in seen:
                seen.add(url)
                unique_images.append(img)
        unique_images = unique_images[:3]

    # Final event — images (suppressed when confidence is low)
    if _is_low_confidence_answer(full_answer):
        yield "\x00" + _json.dumps({"type": "images", "images": []})
    else:
        yield "\x00" + _json.dumps({"type": "images", "images": unique_images})
