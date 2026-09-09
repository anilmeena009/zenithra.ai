# Zenithra.ai — Backend v2 (Hinglish Guide)

Ye version pehle wale se zyada powerful hai — ab isme production-ready features hain:

## Naye Features

| Feature | Kya karta hai |
|---|---|
| **Retry logic** | Gemini fail ho (server error/timeout) to automatically 2 baar retry karta hai (1s, 2s gap ke saath) |
| **Rate limiting** | Ek IP se max 10 requests/minute — spam/abuse rukta hai |
| **Logging** | Har request console pe aur `zenithra.log` file mein save hoti hai |
| **User history** | Har user ke questions/answers SQLite database (`zenithra.db`) mein save hote hain |
| **Personalization** | User ka pehle se most-used language (jaise Python) detect karke future "auto" questions mein use karta hai |
| **Language auto-detect** | Agar `type: "auto"` bhejo, question ke text se khud language pehchan leta hai |
| **Conversation context** | Follow-up questions ke liye pichle 3 Q&A yaad rakhta hai (better answers ke liye) |
| **Response time** | Har response mein pata chalta hai kitna time laga |

## Setup (same as pehle, bas naya folder mein)

### 1. Virtual environment
```
cd zenithra-v2
python -m venv venv
venv\Scripts\activate
```

### 2. Dependencies
```
pip install -r requirements.txt
```
(Koi naya package nahi chahiye — SQLite Python mein already built-in hai)

### 3. API key
```
cp .env.example .env
```
`.env` mein apni Gemini key daalo.

### 4. Run karo
```
uvicorn main:app --reload
```

## Naya Request Format

Ab `user_id` bhi bhejna hai (taaki har user ki alag history track ho):

```json
{
  "user_id": "anil123",
  "question": "Reverse a linked list",
  "type": "auto"
}
```

**`type: "auto"`** ka matlab — backend khud detect karega ki ye Python/C/C++/LeetCode hai ya nahi,
question ke text se ya tumhari past history se.

## Naya Response Format

```json
{
  "best_answer": "...(code/answer)...",
  "best_source": "gemini",
  "detected_type": "python",
  "response_time_ms": 842.5,
  "history_count": 3
}
```

## Apni History Dekhna

Naya endpoint: `GET /history/{user_id}`

Example: `http://127.0.0.1:8000/history/anil123`

Ye tumhare saare past questions aur answers dikhayega (JSON format mein).

## Rate Limit Test Karna

Agar 1 minute mein 10+ requests bhejoge, ye error aayega:
```json
{"detail": "Bahut zyada requests. Max 10 requests per minute allowed hain."}
```
Ye normal hai — 1 minute wait karke phir try karo.

## Logs Dekhna

`zenithra.log` file (usi folder mein banegi) mein har request ka record milega:
```
2026-09-03 12:30:15 | INFO | user=anil123 type=python time=842.5ms question='Reverse a linked list'
```

## Database File

`zenithra.db` naam ki file automatically ban jayegi jab pehli baar server run hoga.
Isme sab users ka history store hota hai. Agar kabhi data reset karna ho, bas is file ko delete kar do
(server restart karne pe nayi ban jayegi).

## Important Note
`user_id` abhi simple text hai — koi real login/authentication system nahi hai. Isका matlab koi bhi
apna khud ka `user_id` bana ke bhej sakta hai. Jab tum real users ke liye launch karoge, tab proper
authentication (login/signup) add karna padega — abhi ke liye testing/learning ke liye ye theek hai.

## Next Steps
1. Frontend banayein jo `/solve` aur `/history` dono endpoints use kare
2. Real authentication add karo (jab users badhein)
3. Deploy karo (Railway/Render)
