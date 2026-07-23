# 🔮 Gmail Deadline Detector

Gmail Deadline Detector is an AI-powered browser extension and local backend designed to scan, parse, and flag deadlines directly from your Gmail inbox. It uses a custom Machine Learning model (TF-IDF Vectorizer + Scikit-Learn Classifier) combined with robust regex-based date extractors to highlight urgent tasks and their due dates.

---

## 🚀 Key Features

*   **AI-Powered Classification:** Uses a machine learning classifier to determine the probability that an email contains a deadline.
*   **Automatic Date Parsing:** A regex-based date finder and normalizer that detects and formats various date representations (e.g., `dd/mm/yyyy`, `Oct 30`, `tomorrow`, `today`).
*   **Secure Gmail Integration:** Connects securely to the official Gmail API using OAuth 2.0 (read-only permission).
*   **Glassmorphic UI:** Features a sleek, futuristic, chrome extension popup UI styled with modern CSS variables, glassmorphism filters, smooth animations, and prediction badges.

---

## 🛠️ Architecture & Tech Stack

### 1. Chrome Extension Frontend (`/chrome_extension`)
*   **Manifest V3:** Fully compliant extension architecture.
*   **Popup UI (`popup.html` / `styles.css`):** Glassmorphism design system (`backdrop-filter`) with custom scrollbars and hover micro-animations.
*   **Logic (`popup.js`):** Interacts with the backend server to fetch results and parses incoming dates gracefully (supporting tomorrow/today and date suffix cleanups).

### 2. FastAPI Backend (`/backend`)
*   **API Framework:** FastAPI with CORS middleware enabled (accepting requests from the Chrome extension).
*   **AI Models (`/backend/models`):** 
    *   `tfidf_vectorizer.pkl`: Text vectorizer.
    *   `deadline_classifier.pkl`: Pre-trained classifier.
*   **Text Preprocessing:** NLTK Stopwords filtering, punctuation cleanup, and case normalization.
*   **Authentication:** `google-auth-oauthlib` and `google-api-python-client` for handling user consent and credential caching (`token.pickle`).

---

## ⚙️ Installation & Setup

### Prerequisites
*   Python 3.10+ installed.
*   Google Chrome (or any Chromium-based browser).
*   A Google Cloud Project with the Gmail API enabled.

---

### Step 1: Set up Gmail API Credentials

To query Gmail, you need your own desktop application client credentials from the Google Cloud Console:

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (e.g., `Gmail Deadline Detector`).
3.  Navigate to **Enabled APIs & Services** and enable the **Gmail API**.
4.  Configure the **OAuth Consent Screen**:
    *   Set the User Type to **External**.
    *   Under **Scopes**, add `https://www.googleapis.com/auth/gmail.readonly`.
    *   Under **Test users**, add the email address of the Gmail account you want to scan.
5.  Create credentials:
    *   Go to the **Credentials** tab.
    *   Click **Create Credentials** -> **OAuth client ID**.
    *   Select **Desktop App** as the application type.
    *   Download the JSON file of the created credentials.
6.  Rename this file to `credentials.json` and place it in the `backend/` directory of the project.

---

### Step 2: Set up the Backend

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Install the required dependencies:
    ```bash
    pip install -r ../requirements.txt
    ```
3.  Start the FastAPI backend with Uvicorn:
    ```bash
    uvicorn app:app --reload
    ```
    *Note: The backend runs by default on `http://127.0.0.1:8000`.*

---

### Step 3: Load the Chrome Extension

1.  Open Google Chrome and navigate to `chrome://extensions/`.
2.  Turn on **Developer mode** (toggle in the top-right corner).
3.  Click **Load unpacked** (button in the top-left corner).
4.  Select the `chrome_extension` folder from this repository.
5.  Pin the **Deadline Detector** extension to your toolbar.

---

## 💡 How to Use

1.  Ensure your FastAPI backend is running.
2.  Click the extension icon in your Chrome toolbar.
3.  Click the **Fetch Deadlines** button.
4.  **First-time Authentication:** A browser window will automatically open, prompting you to log in to your Google Account. Accept the permissions request (since your app is in testing, click "Advanced" and "Go to Quickstart (unsafe)" if Google shows a warning).
5.  Once authorized, your local backend will cache the credentials in `token.pickle`, retrieve your emails, process them with the machine learning model, and display detected deadlines in the extension popup.

---

## 🔒 Security & Privacy

*   **Local Caching:** Your Google OAuth credentials (`token.pickle`) are saved locally on your computer.
*   **Read-Only Scope:** The app only requests the `gmail.readonly` permission scope, ensuring it cannot send, delete, or modify any emails.
*   **Privacy:** All processing (TF-IDF vectorization and classification) happens locally on your machine. No data is sent to external AI servers.
