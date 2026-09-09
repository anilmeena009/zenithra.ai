"""
Zenithra.ai Backend (v2)
-------------------------
Features:
- Google Gemini API (free tier)
- Retry logic (Gemini fail hone pe auto-retry)
- Rate limiting (per IP, spam/abuse rokne ke liye)
- Logging (har request console + file mein log hoti hai)
- User history tracking (SQLite database mein save hoti hai)
- Personalization (past activity ke hisaab se preferred language/type)
- Language auto-detect (agar type na diya ho to question se guess karta hai)
- Conversation context (follow-up questions ke liye pichle Q&A yaad rakhta hai)
- Response time tracking

Run karne ke liye:
    uvicorn main:app --reload
"""

import os
import re
import time
import sqlite3
import logging
import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.1-flash-lite"  # free-tier model — higher daily quota than flash
DB_PATH = os.getenv("DB_PATH", "zenithra.db")

# ---------- Logging Setup ----------
# Har request console pe bhi dikhegi aur "zenithra.log" file mein bhi save hogi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("zenithra.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("zenithra")

app = FastAPI(title="Zenithra.ai")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Database Setup ----------

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                type TEXT NOT NULL,
                answer TEXT,
                source TEXT,
                response_time_ms REAL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON history(user_id)")


init_db()


def save_question(user_id: str, question: str, qtype: str, answer: str,
                   source: str, response_time_ms: float) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO history (user_id, question, type, answer, source, response_time_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, question, qtype, answer, source, response_time_ms,
             datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid


def get_user_history(user_id: str, limit: int = 5):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, question, type, answer FROM history
               WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_question(user_id: str, question_id: int) -> bool:
    """Ek specific history entry delete karta hai. True return karta hai agar kuch delete hua."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM history WHERE id = ? AND user_id = ?",
            (question_id, user_id),
        )
        return cursor.rowcount > 0


def get_preferred_type(user_id: str) -> str | None:
    """User ne sabse zyada kis type (python/cpp/etc) ke questions puche hain, wo dhoondta hai."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT type, COUNT(*) as cnt FROM history
               WHERE user_id = ? AND type != 'auto' AND type != 'general'
               GROUP BY type ORDER BY cnt DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        return row["type"] if row else None


# ---------- Rate Limiting ----------
# Simple in-memory rate limiter: har IP ko max 10 requests/minute

RATE_LIMIT = 10  # requests
RATE_WINDOW = timedelta(minutes=1)
_request_log: dict[str, list[datetime]] = {}


def check_rate_limit(client_ip: str):
    now = datetime.now(timezone.utc)
    timestamps = _request_log.get(client_ip, [])
    # Purani (window se bahar wali) timestamps hata do
    timestamps = [t for t in timestamps if now - t < RATE_WINDOW]

    if len(timestamps) >= RATE_LIMIT:
        logger.warning(f"Rate limit hit by {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Bahut zyada requests. Max {RATE_LIMIT} requests per minute allowed hain."
        )

    timestamps.append(now)
    _request_log[client_ip] = timestamps


# ---------- Language Auto-Detect ----------

LANGUAGE_KEYWORDS = {
    "cpp": [r"\bc\+\+", r"\bcpp\b"],
    "c": [r"\bin c\b(?!\+)", r"\bc language\b", r"\bc programming\b"],
    "python": [r"\bpython\b", r"\bpy\b"],
    "leetcode": [r"\bleetcode\b", r"\bleet code\b"],
}


def detect_type(question: str, requested_type: str, preferred_type: str | None) -> str:
    """
    Agar user ne specific type diya hai (auto ke alawa), usi ko use karo.
    Warna question ke text se guess karo. Agar wo bhi na mile, user ka
    pehle se most-used type use karo. Aakhir mein "general" fallback hai.
    """
    if requested_type and requested_type != "auto":
        return requested_type

    q_lower = question.lower()
    for lang, patterns in LANGUAGE_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, q_lower):
                return lang

    if preferred_type:
        return preferred_type

    return "general"


# ---------- Request/Response Models ----------

class QuestionRequest(BaseModel):
    user_id: str = "guest"
    question: str
    type: str = "auto"  # python | c | cpp | leetcode | theory | general | auto


class AnswerResponse(BaseModel):
    id: int
    best_answer: str
    best_source: str = "gemini"
    detected_type: str
    response_time_ms: float
    history_count: int


# ---------- System Prompt ----------

def build_system_prompt(qtype: str, history: list[dict]) -> str:
    base = (
        "You are a coding assistant. Give SHORT, CONCISE, to-the-point answers. "
        "No lengthy explanations, no restating the question, no unnecessary comments "
        "unless the user explicitly asks for explanation. Just solve the problem directly."
    )
    if qtype == "theory":
        base += (
            " For theory questions, give a crisp, short explanation (max 4-5 lines), "
            "not an essay."
        )
    elif qtype == "leetcode":
        base += (
            " For LeetCode-style problems, give only the optimal code solution with "
            "time/space complexity in one line at the end. No walkthrough unless asked."
        )
    else:
        base += f" The question is related to {qtype}. Only give code, minimal text."

    # Pichle conversation ka context add karo (follow-up questions ke liye)
    if history:
        context_lines = []
        for h in reversed(history):  # purane se naye order mein
            context_lines.append(f"Previous Q: {h['question']}\nPrevious A: {h['answer'][:200]}")
        base += (
            "\n\nConversation history (for context on follow-up questions):\n"
            + "\n---\n".join(context_lines)
        )

    return base


# ---------- Gemini API Call (with retry logic) ----------

async def call_gemini_once(question: str, system_prompt: str) -> tuple[bool, str]:
    """Returns (success, text_or_error)"""
    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY .env file mein missing hai"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": question}]}],
        "generationConfig": {
            "maxOutputTokens": 800,
            "thinkingConfig": {"thinkingLevel": "low"},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 500:
                # Server-side error — retry ke layak hai
                return False, f"Gemini server error {resp.status_code}: {resp.text}"
            if resp.status_code >= 400:
                # Client-side error (bad key, bad model, etc) — retry se fayda nahi
                return False, f"[Gemini error {resp.status_code}: {resp.text}]"
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return False, "Gemini ne koi response nahi diya"
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            return True, text
    except httpx.TimeoutException:
        return False, "Gemini request timeout ho gaya"
    except Exception as e:
        return False, f"Gemini error: {e}"


async def call_gemini_with_retry(question: str, system_prompt: str, max_retries: int = 2) -> str:
    last_error = ""
    for attempt in range(1, max_retries + 2):  # e.g. max_retries=2 -> 3 total attempts
        success, result = await call_gemini_once(question, system_prompt)
        if success:
            if attempt > 1:
                logger.info(f"Gemini call succeeded on attempt {attempt}")
            return result

        last_error = result
        # Agar client error hai (400 wagera), retry karne ka fayda nahi — turant return karo
        if result.startswith("[Gemini error 4"):
            return result

        logger.warning(f"Gemini attempt {attempt} failed: {result}")
        if attempt <= max_retries:
            await asyncio.sleep(1 * attempt)  # 1s, phir 2s backoff

    return f"[Gemini error after {max_retries + 1} attempts: {last_error}]"


# ---------- Main Endpoint ----------

@app.post("/solve", response_model=AnswerResponse)
async def solve(req: QuestionRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question khaali nahi ho sakta")
    if len(req.question) > 2000:
        raise HTTPException(status_code=400, detail="Question bahut lamba hai (max 2000 characters)")

    start_time = time.perf_counter()

    preferred_type = get_preferred_type(req.user_id)
    resolved_type = detect_type(req.question, req.type, preferred_type)
    history = get_user_history(req.user_id, limit=3)

    system_prompt = build_system_prompt(resolved_type, history)
    answer = await call_gemini_with_retry(req.question, system_prompt)

    response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    logger.info(
        f"user={req.user_id} type={resolved_type} time={response_time_ms}ms "
        f"question={req.question[:60]!r}"
    )

    saved_id = save_question(req.user_id, req.question, resolved_type, answer, "gemini", response_time_ms)

    return AnswerResponse(
        id=saved_id,
        best_answer=answer,
        best_source="gemini",
        detected_type=resolved_type,
        response_time_ms=response_time_ms,
        history_count=len(history),
    )


# ---------- History Endpoint (user apni past activity dekh sake) ----------

@app.get("/history/{user_id}")
async def get_history(user_id: str, limit: int = 20):
    history = get_user_history(user_id, limit=limit)
    return {"user_id": user_id, "count": len(history), "history": history}


@app.delete("/history/{user_id}/{question_id}")
async def delete_history_item(user_id: str, question_id: int):
    deleted = delete_question(user_id, question_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ye question nahi mila ya pehle se delete ho chuka hai")
    logger.info(f"Deleted history item {question_id} for user={user_id}")
    return {"status": "deleted", "id": question_id}


@app.delete("/history/{user_id}")
async def delete_all_history(user_id: str):
    """User ki saari history delete kar deta hai."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
    logger.info(f"Deleted {deleted_count} history items for user={user_id}")
    return {"user_id": user_id, "deleted": deleted_count}


@app.delete("/history/{user_id}/{item_id}")
async def delete_history_item(user_id: str, item_id: int):
    """Ek single history item delete karta hai (ID se)."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM history WHERE user_id = ? AND id = ?", (user_id, item_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ye history item nahi mila")
    logger.info(f"Deleted history item id={item_id} for user={user_id}")
    return {"deleted": True, "id": item_id}


@app.get("/")
async def root():
    return {"status": "running", "message": "Zenithra.ai Backend is live"}
