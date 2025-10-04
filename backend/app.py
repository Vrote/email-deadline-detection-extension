import os
import re
import string
import joblib
import base64
import pickle
from typing import List
import json
from datetime import datetime
from dateutil import parser


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import nltk

# Google API imports
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ------------------ Setup ------------------
try:
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words("english"))
except Exception:
    nltk.download("stopwords")
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words("english"))

MODEL_PATH = os.path.join("models", "deadline_classifier.pkl")
VECT_PATH = os.path.join("models", "tfidf_vectorizer.pkl")

if not os.path.exists(MODEL_PATH) or not os.path.exists(VECT_PATH):
    raise FileNotFoundError("Place deadline_classifier.pkl and tfidf_vectorizer.pkl in ./models/")

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECT_PATH)

DATE_PATTERN = (
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]* \d{1,2}\b"
)


def clean_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = text.lower()
    tokens = [w for w in text.split() if w not in stop_words]
    return " ".join(tokens)


def extract_dates(text: str) -> List[str]:
    return re.findall(DATE_PATTERN, text.lower())


# ------------------ FastAPI ------------------
app = FastAPI(title="Deadline Detection API")

# CORS middleware for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # use extension URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextIn(BaseModel):
    email_text: str


class BatchIn(BaseModel):
    email_texts: List[str]


@app.get("/")
def root():
    return {"status": "ok", "message": "Deadline Detection API running. Use POST /predict"}


@app.post("/predict")
def predict_single(payload: TextIn):
    txt = payload.email_text
    if not txt:
        raise HTTPException(status_code=400, detail="No email_text provided")

    cleaned = clean_text(txt)
    X = vectorizer.transform([cleaned])
    prob = float(model.predict_proba(X).max()) if hasattr(model, "predict_proba") else 0.0
    dates_found = extract_dates(txt)

    # Only consider it a deadline if model is confident AND a date is present
    pred = 1 if prob > 0.8 and len(dates_found) > 0 else 0

    return {
        "prediction": pred,
        "probability": prob,
        "dates_found": dates_found,
        "cleaned_text": cleaned,
    }


# ------------------ Cache ------------------
CACHE_FILE = "emails_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"emails": [], "ids": [], "last_email_ts": None}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)


@app.get("/predict_from_gmail")
def predict_from_gmail(max_results: int = 200):
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

    # Load cache
    cache = load_cache()
    processed_ids = set(cache.get("ids", []))
    last_email_ts = cache.get("last_email_ts", None)

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise HTTPException(status_code=500, detail="credentials.json not found")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)

    service = build("gmail", "v1", credentials=creds)

    # Use Gmail search query to fetch only new emails
    query = f"after:{last_email_ts}" if last_email_ts else ""
    results = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"], q=query
    ).execute()

    messages = results.get("messages", [])
    new_emails = []

    for m in messages:
        if m["id"] in processed_ids:
            continue  # Skip already processed emails

        msg = service.users().messages().get(userId="me", id=m["id"]).execute()
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")
        snippet = msg.get("snippet", "")

        # Skip spam/trash
        labels = msg.get("labelIds", [])
        if "SPAM" in labels or "TRASH" in labels:
            continue

        body_text = ""
        parts = msg.get("payload", {}).get("parts", []) or []
        for p in parts:
            if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
                data = p["body"]["data"]
                body_text += base64.urlsafe_b64decode(data).decode("utf-8")

        full_text = (snippet + "\n" + body_text).strip()
        cleaned = clean_text(full_text)
        X = vectorizer.transform([cleaned])
        prob = float(model.predict_proba(X).max()) if hasattr(model, "predict_proba") else 0.0
        dates_found = extract_dates(full_text)
        pred = 1 if prob > 0.8 and len(dates_found) > 0 else 0

        if pred == 1:
            email_data = {
                "id": m["id"],
                "subject": subject,
                "from": sender,
                "date": date,
                "prediction": pred,
                "dates_found": dates_found,
                "snippet": snippet,
            }
            new_emails.append(email_data)
            cache["emails"].append(email_data)
            cache["ids"].append(m["id"])

    # Update last_email_ts to latest email timestamp
    timestamps = []
    for e in new_emails:
       try:
         ts = int(parser.parse(e["date"]).timestamp())
         timestamps.append(ts)
       except:
         continue
    if timestamps:
       cache["last_email_ts"] = max(timestamps)



    # Save cache
    save_cache(cache)

    # Return cached emails (old + new)
    return {"count": len(cache["emails"]), "emails": cache["emails"]}
