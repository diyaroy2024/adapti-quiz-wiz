# NLP Question Paper Generation — FastAPI Backend

Python NLP service that powers the React frontend's `/generate` flow.

| Layer | Tech |
| --- | --- |
| API | FastAPI + Uvicorn |
| Keywords / concepts | KeyBERT |
| Semantic understanding | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Question generation | T5 / BART (`valhalla/t5-base-qg-hl`, BART fallback) |
| Linguistics | spaCy + NLTK |
| Bloom's Taxonomy | verb templates + sentence-embedding classifier |
| Storage (optional) | MongoDB via PyMongo |

## 1. Setup

```bash
cd backend
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

First run downloads the HuggingFace models (~1 GB) into `~/.cache/huggingface`.

## 2. Run

```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 2.5 MongoDB Atlas setup (free, 10 minutes)

1. Go to https://www.mongodb.com/cloud/atlas/register and create a free account.
2. **Create a cluster** → choose **M0 / Free** → any cloud + region near you → Create.
3. **Database Access** (left menu) → *Add New Database User* → Authentication:
   Password → username e.g. `qpgen` → click *Autogenerate Secure Password* and
   **copy it** → Role: *Read and write to any database* → Add User.
4. **Network Access** → *Add IP Address* → *Allow access from anywhere*
   (`0.0.0.0/0`) for local development → Confirm.
5. **Clusters → Connect → Drivers → Python** → copy the connection string. It
   looks like:
   `mongodb+srv://qpgen:<db_password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority`
6. In `backend/`, copy `.env.example` to `.env` and paste the string into
   `MONGODB_URI`, replacing `<db_password>` with the password from step 3.
   Set `JWT_SECRET` to any long random string (`openssl rand -hex 32`).
7. Restart uvicorn. `GET http://localhost:8000/health` should now report the
   database as ready, and `/auth/status` should return `accountsEnabled: true`.

The `.env` file is git-ignored — credentials never reach the frontend or the repo.
Collections (`users`, `documents`, `questions`, `papers`, `analytics`) and their
indexes are created automatically on the first connection.

## 3. Environment variables (all optional)

Copy `backend/.env.example` to `backend/.env` and fill it in:

```bash
QG_MODEL=valhalla/t5-base-qg-hl        # any T5/BART question-generation checkpoint
EMBED_MODEL=all-MiniLM-L6-v2           # Sentence-Transformers model
MONGODB_URI=mongodb://localhost:27017  # omit to disable persistence
MONGODB_DB=qpgen
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5173
```

## 4. Connect the frontend

In the project root create `.env`:

```bash
VITE_BACKEND_URL=http://localhost:8000
```

Restart the Vite dev server. Without this variable the frontend uses its built-in
offline mock generator.

## 5. API

### `POST /generate`

```json
{
  "title": "Unit Test 1 — NLP",
  "text": "<syllabus / extracted PDF text>",
  "config": {
    "language": "en",
    "totalMarks": 50,
    "bloomLevels": ["remember", "understand", "apply", "analyze"],
    "types": ["mcq", "fill", "descriptive"],
    "difficultyMix": { "easy": 30, "medium": 50, "hard": 20 },
    "topicHint": "Unit 1: Text preprocessing"
  }
}
```

Response — `GeneratedPaper` (identical shape to `src/lib/types.ts`):

```json
{
  "id": "…",
  "title": "Unit Test 1 — NLP",
  "createdAt": "2026-01-01T00:00:00Z",
  "config": { "…": "…" },
  "sourcePreview": "first 300 chars…",
  "questions": [
    {
      "id": "…",
      "type": "mcq",
      "bloom": "understand",
      "difficulty": "medium",
      "marks": 2,
      "question": "…",
      "options": ["…"],
      "answer": "…",
      "keywords": ["tokenization"],
      "topic": "Tokenization",
      "co": "CO1"
    }
  ]
}
```

### Other endpoints

- `GET /health` — service + model status
- `GET /papers?limit=20` — recent papers (requires MongoDB)

## Pipeline

```text
PDF / DOCX / text  →  sentence segmentation (spaCy/NLTK)
                   →  KeyBERT concept extraction
                   →  Sentence-Transformers context retrieval
                   →  T5/BART question generation
                   →  Bloom's Taxonomy classification
                   →  difficulty + marks blueprint
                   →  Course Outcome mapping
                   →  GeneratedPaper JSON
```

## Troubleshooting

- **Slow first request** — models load lazily on the first `/generate` call.
- **`OSError: [E050] Can't find model 'en_core_web_sm'`** — run the spaCy download step.
- **CORS errors** — add your frontend origin to `ALLOWED_ORIGINS`.
- **Torch install fails** — install a matching wheel from https://pytorch.org first, then re-run `pip install -r requirements.txt`.
