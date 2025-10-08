import os
import re
import string
import joblib
import base64
import pickle
from typing import List
import logging
from dateutil import parser

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import nltk

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------- NLTK Setup ----------------
try:
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words("english"))
except Exception:
    nltk.download("stopwords")
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words("english"))

# ---------------- Model Setup ----------------
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

# ---------------- Utility Functions ----------------
def clean_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = text.lower()
    tokens = [w for w in text.split() if w not in stop_words]
    return " ".join(tokens)

def extract_dates(text: str) -> List[str]:
    return re.findall(DATE_PATTERN, text.lower())

# ---------------- FastAPI Setup ----------------
app = FastAPI(title="Deadline Detection API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accept requests from Chrome extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Request Models ----------------
class TextIn(BaseModel):
    email_text: str

# ---------------- Routes ----------------
@app.get("/")
def root():
    return {"status": "ok", "message": "Deadline Detection API running."}

@app.post("/predict")
def predict_single(payload: TextIn):
    txt = payload.email_text
    if not txt:
        raise HTTPException(status_code=400, detail="No email_text provided")

    cleaned = clean_text(txt)
    X = vectorizer.transform([cleaned])
    prob = float(model.predict_proba(X).max()) if hasattr(model, "predict_proba") else 0.0
    dates_found = extract_dates(txt)
    pred = 1 if prob > 0.8 and len(dates_found) > 0 else 0

    return {
        "prediction": pred,
        "dates_found": dates_found,
        "cleaned_text": cleaned,
    }

@app.get("/predict_from_gmail")
def predict_from_gmail(max_results: int = 40):
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

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

    messages = []
    next_page_token = None
    fetched_count = 0

    while fetched_count < max_results:
        results = service.users().messages().list(
            userId="me",
            maxResults=min(100, max_results - fetched_count),
            labelIds=["INBOX"],
            pageToken=next_page_token
        ).execute()
        batch = results.get("messages", [])
        messages.extend(batch)
        fetched_count += len(batch)
        next_page_token = results.get("nextPageToken")
        if not next_page_token or not batch:
            break

    logging.info(f"Fetched {len(messages)} emails from Gmail")
    deadline_emails = []

    for m in messages:
        try:
            msg = service.users().messages().get(userId="me", id=m["id"]).execute()
            headers = msg.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")
            snippet = msg.get("snippet", "")

            labels = msg.get("labelIds", [])
            if "SPAM" in labels or "TRASH" in labels:
                continue

            body_text = ""
            parts = msg.get("payload", {}).get("parts", []) or []
            for p in parts:
                if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
                    try:
                        data = p["body"]["data"]
                        body_text += base64.urlsafe_b64decode(data).decode("utf-8")
                    except Exception as e:
                        logging.warning(f"Failed to decode email {m['id']}: {e}")

            full_text = (snippet + "\n" + body_text).strip()
            cleaned = clean_text(full_text)
            X = vectorizer.transform([cleaned])
            prob = float(model.predict_proba(X).max()) if hasattr(model, "predict_proba") else 0.0
            dates_found = extract_dates(full_text)
            pred = 1 if prob > 0.8 and len(dates_found) > 0 else 0

            if pred == 1:
                deadline_emails.append({
                    "id": m["id"],
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "prediction": pred,
                    "probability": prob,
                    "dates_found": dates_found,
                    "snippet": snippet,
                })

        except Exception as e:
            logging.error(f"Error processing email {m.get('id', 'Unknown')}: {e}")
            continue

    return {"count": len(deadline_emails), "emails": deadline_emails}
