# backend/app.py
import os, shutil, uuid, re, json
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from docx import Document
from dotenv import load_dotenv
from datetime import datetime
import re, json
from placeholder_hints import generate_hint

from db import Base, engine, SessionLocal
from models import Session as Sess, Document as DocModel, Placeholder, Message, Suggestion
from docx_parser import find_placeholders, fill_placeholders
from placeholder_engine import normalize_key
from render_service import docx_to_html

load_dotenv()
os.makedirs("data", exist_ok=True)
Base.metadata.create_all(bind=engine)

from groq import Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
GROQ_MODEL = "llama-3.1-8b-instant"

app = FastAPI(title="Lexsy Legal Doc Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def db_sess():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ---------- helpers ----------
def placeholder_type_guess(key: str) -> str:
    k = normalize_key(key)
    if "date" in k: return "DATE"
    if any(t in k for t in ["amount","price","cap","valuation","purchase","principal","dollar"]): return "MONEY"
    if any(t in k for t in ["company","corporation","inc","llc"]): return "COMPANY"
    if any(t in k for t in ["investor","name","title"]): return "PERSON"
    if any(t in k for t in ["state","jurisdiction","country","address","city"]): return "TEXT"
    return "TEXT"

def make_preview(doc: DocModel):
    doc.html_preview = docx_to_html(doc.working_docx_path)

def extract_json_safe(text: str) -> dict:
    try: return json.loads(text)
    except: pass
    m = re.search(r"\{(?:[^{}]|(?R))*\}", text, flags=re.S)
    if m:
        try: return json.loads(m.group(0))
        except: return {}
    return {}

# ---------- routes ----------
@app.post("/api/upload")
def upload_doc(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx supported")
    session_id = str(uuid.uuid4())
    db = next(db_sess())
    db.add(Sess(id=session_id, original_filename=file.filename)); db.commit()

    original_path = f"data/{session_id}_orig.docx"
    with open(original_path, "wb") as f: shutil.copyfileobj(file.file, f)
    working_path = f"data/{session_id}_work.docx"; shutil.copyfile(original_path, working_path)
    d = Document(working_path); d.save(working_path)

    placeholders = find_placeholders(working_path)
    doc_rec = DocModel(id=str(uuid.uuid4()), session_id=session_id,
                       original_docx_path=original_path, working_docx_path=working_path)
    db.add(doc_rec); db.commit(); make_preview(doc_rec); db.commit()

    for k in placeholders:
        db.add(Placeholder(session_id=session_id, key=k,
               normalized_key=normalize_key(k), is_filled=False))
    db.commit()

    return {"session_id": session_id,
            "placeholders": [{"key": k, "type": placeholder_type_guess(k)} for k in placeholders]}

@app.get("/api/placeholders")
def list_placeholders(session_id: str):
    db = next(db_sess())
    rows = db.query(Placeholder).filter(Placeholder.session_id==session_id).all()
    return [{"key": r.key, "is_filled": r.is_filled, "value": r.value, "type": placeholder_type_guess(r.key)} for r in rows]

@app.get("/api/render")
def render(session_id: str):
    db = next(db_sess())
    doc = db.query(DocModel).filter(DocModel.session_id==session_id).first()
    if not doc: raise HTTPException(404, "Session not found")
    return JSONResponse({"html": doc.html_preview})

@app.get("/api/download")
def download(session_id: str):
    db = next(db_sess())
    doc = db.query(DocModel).filter(DocModel.session_id==session_id).first()
    if not doc: raise HTTPException(404, "Session not found")
    return FileResponse(path=doc.working_docx_path, filename="completed.docx",
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.post("/api/fill")
def fill(session_id: str = Form(...), key: str = Form(...), value: str = Form(...)):
    db = next(db_sess())
    doc = db.query(DocModel).filter(DocModel.session_id==session_id).first()
    if not doc: raise HTTPException(404, "Session not found")

    rows = db.query(Placeholder).filter(Placeholder.session_id==session_id).all()
    target = None
    for r in rows:
        if r.key == key or r.normalized_key == normalize_key(key):
            target = r; break
    if not target: raise HTTPException(404, "Placeholder not found")
    target.value = value; target.is_filled = True; db.commit()
    mapping = {r.key: r.value for r in rows if r.is_filled and r.value}
    fill_placeholders(doc.original_docx_path, doc.working_docx_path, mapping); make_preview(doc); db.commit()
    return {"ok": True}

@app.post("/api/fill-bulk")
def fill_bulk(session_id: str = Form(...), mapping_json: str = Form(...)):
    db = next(db_sess())
    doc = db.query(DocModel).filter(DocModel.session_id==session_id).first()
    if not doc: raise HTTPException(404, "Session not found")
    mapping = json.loads(mapping_json)
    rows = db.query(Placeholder).filter(Placeholder.session_id==session_id).all()
    for r in rows:
        for k,v in mapping.items():
            if r.key == k or r.normalized_key == normalize_key(k):
                r.value = v; r.is_filled = True
    db.commit()
    eff = {r.key: r.value for r in rows if r.is_filled and r.value}
    fill_placeholders(doc.original_docx_path, doc.working_docx_path, eff); make_preview(doc); db.commit()
    return {"ok": True}

# ---- Chat (suggest only, do not auto-apply) ----
@app.get("/api/messages")
def messages(session_id: str):
    db = next(db_sess())
    msgs = db.query(Message).filter(Message.session_id==session_id).all()
    return [{"role": m.role, "content": m.content} for m in msgs]

@app.post("/api/chat")
def chat(session_id: str = Form(...), message: str = Form(...)):
    """
    Document-agnostic, pending-only extraction using Groq (mixtral-8x7b-instruct),
    with semantic hints and strong validations. Returns JSON-only suggestions.
    """
    db = next(db_sess())

    # Store user message in history
    db.add(Message(session_id=session_id, role="user", content=message))
    db.commit()

    # Load placeholders and determine pending ones
    all_ph = db.query(Placeholder).filter(Placeholder.session_id == session_id).all()
    pending = [p for p in all_ph if not p.is_filled]

    if not pending:
        msg = "All placeholders are already filled 🎉"
        db.add(Message(session_id=session_id, role="assistant", content=msg))
        db.commit()
        return {"reply": msg, "suggestions": {}}

    # Build pending list with types + HINTS
    pending_list = [{"key": p.key, "type": placeholder_type_guess(p.key), "hint": generate_hint(p.key)} for p in pending]
    pending_keys = set(p["key"] for p in pending_list)
    type_by_key = {p["key"]: p["type"] for p in pending_list}

    # ---------------------------------------------------------
    # Helpers: normalization & regex fallbacks
    # ---------------------------------------------------------
    current_year = datetime.now().year

    def normalize_money(raw: str) -> str:
        # Capture forms like "4000 $", "$4000", "4,000", "4k" (we won't expand 4k here)
        # Strip everything except digits and dots/commas
        s = raw.strip()
        # cases like "4000 $" -> put $ first
        s = re.sub(r"^(\d[\d,\.]*)\s*\$$", r"$\1", s)
        # extract numeric core
        m = re.search(r"(\d[\d,\.]*)", s)
        if not m:
            return raw
        num = m.group(1).replace(",", "")
        try:
            val = float(num)
            return f"${val:,.0f}" if val.is_integer() else f"${val:,.2f}"
        except:
            return f"${m.group(1)}"

    MONTHS = {
        "jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May", "jun": "June",
        "jul": "July", "aug": "August", "sep": "September", "oct": "October", "nov": "November", "dec": "December"
    }

    def normalize_date_phrase(text: str) -> str:
        t = text.lower().strip()
        current_year = datetime.now().year
        year = current_year

        if "last year" in t:
            year -= 1
            t = t.replace("last year", "")
        elif "next year" in t:
            year += 1
            t = t.replace("next year", "")
        elif "this year" in t:
            t = t.replace("this year", "")
        else:
            # If no relative year term, keep current year by default
            pass

        # D Mon  →  1 jan
        m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", t)
        if m:
            day = int(m.group(1))
            month = MONTHS[m.group(2)]
            return f"{month} {day}, {year}"

        # Mon D  →  jan 1
        m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)
        if m:
            month = MONTHS[m.group(1)]
            day = int(m.group(2))
            return f"{month} {day}, {year}"

        # 01/02 or 1-2-25 type
        m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
        if m:
            m1, d1, y = int(m.group(1)), int(m.group(2)), m.group(3)
            y = int(y) if y else year
            if y < 100:
                y += 2000
            month_name = list(MONTHS.values())[m1-1] if 1 <= m1 <= 12 else "January"
            return f"{month_name} {d1}, {y}"

        # If nothing matched, return original
        return text

    # Fallback REGEX extractors (only applied if LLM returns nothing)
    def fallback_extract_money(msg: str) -> str | None:
        # Find $4,000 or 4000 $ or 4000
        m = re.search(r"(\$\s*\d[\d,\.]*|\d[\d,\.]*\s*\$|\b\d[\d,\.]*\b)", msg)
        if not m: return None
        return normalize_money(m.group(1))

    def fallback_extract_date(msg: str) -> str | None:
        # Try phrase normalization
        out = normalize_date_phrase(msg)
        return out if out != msg else None

    # ---------------------------------------------------------
    # Build strict system & user prompts
    # ---------------------------------------------------------
    system = (
        "You are a legal placeholder extraction assistant for Future equity investment agreement document.\n"
        "You must return ONLY a JSON object.\n"
        "You may ONLY include keys from the pending placeholder list provided.\n"
        "For each key, use the 'hint' to decide if the user message provides that value.\n"
        "If the user message does not clearly provide a value for a placeholder, return null for that key, or omit it.\n"
        "NEVER invent data. NEVER output extra keys. No explanations.\n"
        "Formatting:\n"
        "- COMPANY → UPPERCASE (add ', INC.' ONLY if explicitly stated)\n"
        "- PERSON → Proper Case (Jane Doe)\n"
        "- DATE → Month D, YYYY (honor 'this year', 'last year', 'current year')\n"
        "- MONEY → $X,XXX or $X,XXX,XXX (prefix with $)\n"
    )

    user = (
        "Pending placeholders (key, type, hint):\n"
        f"{json.dumps(pending_list, indent=2)}\n\n"
        f"User message:\n{message}\n\n"
        "Return ONLY a JSON mapping for the pending keys where the message clearly provides the value.\n"
        "If the message doesn't provide a value for a pending key, omit that key or set it to null."
    )

    ai_mapping = {}
    try:
        if groq_client:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=512,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
            )
            raw = (resp.choices[0].message.content or "").strip()
            ai_mapping = extract_json_safe(raw)
        else:
            ai_mapping = {}
    except Exception as e:
        print("Groq error:", e)
        ai_mapping = {}

    # Keep only pending keys and non-null values
    clean = {}
    for k, v in (ai_mapping or {}).items():
        if k in pending_keys and v not in [None, "", "null"]:
            clean[k] = str(v).strip()

    # Post-format by expected type (money/date polish)
    for k, v in list(clean.items()):
        t = type_by_key.get(k, "TEXT")
        if t == "MONEY":
            clean[k] = normalize_money(v)
        elif t == "DATE":
            clean[k] = normalize_date_phrase(v)

    # If LLM returned nothing, try regex fallbacks for single-intent messages
    if not clean:
        # If any MONEY pending and message contains a numeric currency — extract
        money_keys = [k for k in pending_keys if type_by_key.get(k) == "MONEY"]
        if money_keys:
            mval = fallback_extract_money(message)
            if mval:
                # If only one money field, assign directly
                if len(money_keys) == 1:
                    clean[money_keys[0]] = mval
                else:
                    def score_money_key(k: str) -> int:
                        lk = k.lower()
                        hk = generate_hint(k).lower()
                        tokens = ["purchase", "price", "amount", "consideration", "principal", "cap", "valuation"]
                        return sum(t in lk for t in tokens) + sum(t in hk for t in tokens)
                    best = sorted(money_keys, key=score_money_key, reverse=True)[0]
                    clean[best] = mval


        # If any DATE pending and message looks like a date
        date_keys = [k for k in pending_keys if type_by_key.get(k) == "DATE"]
        if date_keys:
            dval = fallback_extract_date(message)
            if dval:
                clean[date_keys[0]] = dval  # safe default: first pending date

    if not clean:
        msg = "No valid placeholder values detected."
        db.add(Message(session_id=session_id, role="assistant", content=msg))
        db.commit()
        return {"reply": msg, "suggestions": {}}

    # Store as 'pending' suggestions for approval
    for k, v in clean.items():
        db.add(Suggestion(session_id=session_id, key=k, value=v, status="pending"))
    db.commit()

    assistant_msg = f"Suggested values: {json.dumps(clean, indent=2)}"
    db.add(Message(session_id=session_id, role="assistant", content=assistant_msg))
    db.commit()

    return {"reply": assistant_msg, "suggestions": clean}

@app.post("/api/apply-suggestion")
def apply_suggestion(session_id: str = Form(...), key: str = Form(...), value: str = Form(...)):
    db = next(db_sess())
    doc = db.query(DocModel).filter(DocModel.session_id==session_id).first()
    if not doc: raise HTTPException(404, "Session not found")

    # mark suggestion accepted
    sug = db.query(Suggestion).filter(Suggestion.session_id==session_id, Suggestion.key==key, Suggestion.value==value, Suggestion.status=="pending").first()
    if sug: sug.status = "accepted"

    # set placeholder
    r = db.query(Placeholder).filter(Placeholder.session_id==session_id).all()
    target = None
    for p in r:
        if p.key == key or p.normalized_key == normalize_key(key):
            target = p; break
    if not target: raise HTTPException(404, "Placeholder not found")
    target.value = value; target.is_filled = True; db.commit()

    mapping = {x.key: x.value for x in r if x.is_filled and x.value}
    fill_placeholders(doc.original_docx_path, doc.working_docx_path, mapping); make_preview(doc); db.commit()
    return {"ok": True}

@app.post("/api/reject-suggestion")
def reject_suggestion(session_id: str = Form(...), key: str = Form(...), value: str = Form(...)):
    db = next(db_sess())
    sug = db.query(Suggestion).filter(Suggestion.session_id==session_id, Suggestion.key==key, Suggestion.value==value, Suggestion.status=="pending").first()
    if sug: sug.status = "rejected"; db.commit()
    return {"ok": True}
