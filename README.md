# MyChatAI — Embeddable AI Chatbot Builder

MyChatAI is a full-stack SaaS platform that lets you create and embed a custom AI-powered chatbot on **any website** in minutes. Point it at a URL, upload a document, or add FAQs — the chatbot learns from your content and answers visitor questions intelligently, with real-time streaming and automatic product image matching.

---

## ✨ Features

- **One-click website training** — Scrape any website and train the chatbot on its content via a live SSE progress stream
- **Multi-source knowledge ingestion** — URLs, PDF files, DOCX files, and manual FAQ pairs
- **RAG-powered answers** — Retrieval-Augmented Generation using Qdrant vector search + Google Gemini 2.5 Flash
- **Streaming responses** — Token-by-token chat streaming via Server-Sent Events
- **Smart image matching** — Automatically attaches relevant product images to answers for e-commerce/Shopify sites
- **Context-aware conversations** — Conversation history, vague follow-up resolution, and pronoun disambiguation
- **Query expansion** — Semantic synonym expansion for contact, pricing, shipping, and more
- **Site-type detection** — Automatically classifies websites (Shopify, e-commerce, restaurant, real estate, education, service) and applies intelligent scraping caps per URL group
- **Embeddable widget** — One `<script>` tag to add the chatbot bubble to any site (HTML, WordPress, Shopify, Wix, Webflow, Squarespace, Joomla, Drupal)
- **User authentication** — JWT-based auth with email/password registration + Google OAuth
- **Bot management dashboard** — Create, configure, and manage multiple chatbots per account

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js 16)                  │
│  Landing Page · Dashboard · Build Wizard · Auth Pages       │
└────────────────────────┬────────────────────────────────────┘
                         │ REST / SSE
┌────────────────────────▼────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                             │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  auth_router │  │  train_router  │  │  chat_router   │  │
│  │  /auth/*     │  │  /train/*      │  │  /chat/*       │  │
│  └──────────────┘  └───────┬────────┘  └───────┬────────┘  │
│                            │                   │            │
│  ┌─────────────────────────▼────────────────────▼────────┐  │
│  │                    Services                           │  │
│  │  scraper_firecrawl · image_extractor · chunker        │  │
│  │  embedder (all-MiniLM-L6-v2) · qdrant_service        │  │
│  │  rag_service (Gemini 2.5 Flash)                       │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────┬──────────────────────┬───────────────────────┘
                │                      │
   ┌────────────▼──────────┐  ┌───────▼──────────────┐
   │   Qdrant (Vector DB)  │  │  SQLite (Users/Bots)  │
   │   localhost:6333      │  │  chatbot.db           │
   └───────────────────────┘  └──────────────────────┘
```

---

## 🗂️ Project Structure

```
Chatbot/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   ├── database.py            # SQLAlchemy async engine + session
│   │   ├── user.py                # User ORM model
│   │   └── bot.py                 # Bot ORM model
│   ├── routers/
│   │   ├── auth_router.py         # Register, login, Google OAuth, /me
│   │   ├── bot_router.py          # CRUD for bots
│   │   ├── train_router.py        # URL / file / FAQ training endpoints
│   │   └── chat_router.py         # Chat + streaming endpoints
│   ├── schemas/
│   │   └── auth.py                # Pydantic request/response schemas
│   └── services/
│       ├── scraper_firecrawl.py   # Web scraper (Firecrawl + content cleaning)
│       ├── image_extractor.py     # Product image extraction pipeline
│       ├── chunker.py             # LangChain text splitter
│       ├── embedder.py            # SentenceTransformers (all-MiniLM-L6-v2)
│       ├── qdrant_service.py      # Qdrant vector DB client
│       ├── rag_service.py         # RAG pipeline + Gemini LLM
│       └── bot_service.py         # Bot lookup helpers
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Landing page
│   │   ├── dashboard/             # Bot management dashboard
│   │   ├── build/                 # Chatbot build wizard (train + configure + deploy)
│   │   ├── auth/                  # Google OAuth callback handler
│   │   ├── login/                 # Login page
│   │   ├── register/              # Register page
│   │   └── account/               # Account settings
│   └── components/
│       ├── LiveChatPreview.tsx    # Real-time chat preview with streaming
│       └── AddKnowledgeModal.tsx  # Modal for adding files + FAQs
└── widget/
    └── test.html                  # Widget embed test page
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript, TailwindCSS 4, shadcn/ui |
| **Backend** | FastAPI, Python 3.11+, Uvicorn |
| **LLM** | Google Gemini 2.5 Flash (`google-genai`) |
| **Embeddings** | `all-MiniLM-L6-v2` via `sentence-transformers` |
| **Vector DB** | Qdrant (local instance) |
| **Database** | SQLite + SQLAlchemy (async, `aiosqlite`) |
| **Web Scraping** | Firecrawl (self-hosted), BeautifulSoup, httpx |
| **Auth** | JWT (`python-jose`), bcrypt (`passlib`), Google OAuth 2.0 |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Qdrant](https://qdrant.tech/documentation/quick-start/) running locally on port `6333`
- [Firecrawl](https://github.com/mendableai/firecrawl) running locally on port `3002`
- A [Google Gemini API key](https://aistudio.google.com/apikey)

---

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/chatbot.git
cd chatbot
```

---

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
```

Edit `.env` with your actual values:

```env
GEMINI_API_KEY=your_gemini_api_key_here
QDRANT_HOST=localhost
QDRANT_PORT=6333
DATABASE_URL=sqlite+aiosqlite:///./chatbot.db

# Auth
SECRET_KEY=your_secret_key_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
FRONTEND_URL=http://localhost:3000
```

Start the backend server:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

### 4. Start Qdrant (Docker)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

---

### 5. Start Firecrawl (Self-hosted)

Follow the [Firecrawl self-hosting guide](https://github.com/mendableai/firecrawl/tree/main/apps/api#self-hosted) and start it on port `3002`.

---

## 🔑 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `QDRANT_HOST` | Qdrant host (default: `localhost`) | ✅ |
| `QDRANT_PORT` | Qdrant port (default: `6333`) | ✅ |
| `DATABASE_URL` | SQLite async connection string | ✅ |
| `SECRET_KEY` | JWT signing secret | ✅ |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Optional |
| `FRONTEND_URL` | Frontend base URL for OAuth redirect | Optional |

---

## 📡 API Endpoints

### Auth (`/auth`)
| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and get JWT token |
| `GET` | `/auth/google` | Initiate Google OAuth flow |
| `GET` | `/auth/google/callback` | Google OAuth callback |
| `GET` | `/auth/me` | Get current user info |
| `PATCH` | `/auth/change-password` | Change user password |

### Bots (`/bots`)
| Method | Path | Description |
|---|---|---|
| `POST` | `/bots/` | Create a new bot |
| `GET` | `/bots/` | List all bots for current user |
| `GET` | `/bots/{bot_id}` | Get bot details |
| `PATCH` | `/bots/{bot_id}` | Update bot configuration |
| `DELETE` | `/bots/{bot_id}` | Delete a bot |

### Training (`/train`)
| Method | Path | Description |
|---|---|---|
| `POST` | `/train/url/stream` | Train from URL with SSE progress stream |
| `POST` | `/train/url` | Train from URL (non-streaming fallback) |
| `POST` | `/train/file` | Train from PDF or DOCX file upload |
| `POST` | `/train/faq` | Train from FAQ list |
| `DELETE` | `/train/{bot_id}` | Clear all training data for a bot |

### Chat (`/chat`)
| Method | Path | Description |
|---|---|---|
| `POST` | `/chat/` | Get a single answer (non-streaming) |
| `POST` | `/chat/stream` | Get a streaming answer via SSE |

---

## 🧠 How the RAG Pipeline Works

1. **Scraping** — Firecrawl crawls the target website; content is cleaned (boilerplate removed, noise filtered), and URLs are prioritized by type (FAQ, pricing, about > products > blog)
2. **Image Extraction** — Images are extracted from 4 sources: Shopify `/products.json` feed, XML sitemaps, JSON-LD schema tags, and Open Graph tags
3. **Chunking** — Content is split into overlapping chunks using LangChain's text splitter
4. **Embedding** — Each chunk is embedded using `all-MiniLM-L6-v2` (384-dim vectors) and stored in Qdrant along with matched product images
5. **Retrieval** — At query time, the question is expanded with synonyms, embedded, and the top-20 most similar chunks are retrieved from Qdrant
6. **Generation** — Retrieved chunks are assembled into a structured prompt and sent to Gemini 2.5 Flash; the response streams back token by token
7. **Image Matching** — For specific-product queries, images are matched by token overlap against the product name; for category queries, images are matched post-generation by checking which product names appear in the answer

---

## 🛒 Shopify / E-commerce Support

The scraper includes dedicated handling for Shopify and e-commerce sites:

- Fetches the `/products.json` feed to get structured product data (name, price, variants, description, tags)
- Matches product images using a 3-pass strategy: direct substring → token overlap → keyword index fallback
- Classifies queries as "specific product" vs "category" and adjusts retrieval, prompting, and image display accordingly
- Handles geo-blocked sites by falling back to the product feed when standard scraping is blocked

---

## 🌐 Embedding the Widget

After training your bot, copy the embed snippet from the **Deploy** step:

```html
<script src="http://localhost:3000/widget.js" data-bot-id="YOUR_BOT_ID"></script>
```

Paste it before the closing `</body>` tag of any webpage. The chatbot bubble will appear automatically. Platform-specific instructions are available in the Build UI for:

**HTML · WordPress · Shopify · Wix · Squarespace · Webflow · Joomla · Drupal**

---

## 📁 Supported Training Sources

| Source | Format |
|---|---|
| Website URL | Any public webpage or website |
| File upload | `.pdf` (PyMuPDF), `.docx` (python-docx) |
| FAQ pairs | JSON list of `{ question, answer }` |

---

## 🔒 Authentication

- **Email/Password** — Registration + login with bcrypt-hashed passwords and 7-day JWT tokens
- **Google OAuth 2.0** — One-click sign-in; accounts are linked by Google ID or email address

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.