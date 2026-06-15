# Daily DSA Refresher

A full-stack refresher app for competitive programming practice. The backend samples either a curated DSA topic or one of your solved problems, asks an LLM for concise JSON, validates it, and the frontend renders a clean daily revision card.

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Groq or Gemini API key

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and fill in one provider key. For example, keep `LLM_PROVIDER=groq` and set `GROQ_API_KEY`.

## Run Backend

```bash
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`.

## Frontend Setup

```bash
cd frontend
npm install
```

## Run Frontend

```bash
npm run dev
```

The Vite app runs at `http://localhost:5173`.

## Add Problems

Edit `backend/data/problems.txt` and add one supported problem URL per line:

```txt
https://leetcode.com/problems/trapping-rain-water/
https://codeforces.com/problemset/problem/1000/C
```

Lines starting with `#` are ignored. Supported platforms are LeetCode, Codeforces, CodeChef, and AtCoder. You can also add problems with:

```bash
curl -X POST http://localhost:8000/api/problems/add \
  -H "Content-Type: application/json" \
  -d '{"url":"https://leetcode.com/problems/two-sum/"}'
```

When using Supabase, apply `backend/supabase_daily_bite_pointer.sql` once. The daily My Problem bite is selected by `created_at` order, shows the current pointer row, immediately advances the pointer to the next row, and wraps back to the oldest row after the latest row.

## Future: WhatsApp Integration

The `/api/random-topic` and `/api/my-problems` endpoints are already WhatsApp-webhook-ready: they accept simple HTTP requests and return structured refresher content. To add WhatsApp delivery, create a Twilio or WhatsApp Business webhook that calls one of these endpoints, formats the JSON into a compact message, and sends it back to the user.
