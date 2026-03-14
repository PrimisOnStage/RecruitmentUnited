"""Gmail ingestion pipeline for harvesting resume attachments from email.

The flow is:
1. authenticate with the Gmail API,
2. search recent emails that likely contain PDF resumes,
3. score each message to avoid unrelated PDFs,
4. download the attachment temporarily, and
5. reuse the resume parser to produce candidate records.
"""

import base64
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

try:
    from backend.ingest.resume import parse_resume
except ImportError:
    from ingest.resume import parse_resume

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "token.json")
DEFAULT_GMAIL_QUERY = "has:attachment filename:pdf"
GMAIL_QUERY = os.getenv("GMAIL_ATTACHMENT_QUERY", DEFAULT_GMAIL_QUERY)
RESUME_SCORE_THRESHOLD = float(os.getenv("GMAIL_RESUME_SCORE_THRESHOLD", "2.5"))

POSITIVE_KEYWORDS = {
    "resume",
    "cv",
    "application",
    "applicant",
    "candidate",
    "job",
    "hiring",
    "position",
    "cover letter",
    "curriculum vitae",
}

NEGATIVE_KEYWORDS = {
    "invoice",
    "receipt",
    "statement",
    "quote",
    "quotation",
    "brochure",
    "catalog",
    "agenda",
    "minutes",
    "ticket",
}


def _score_resume_likelihood(subject: str, sender: str, snippet: str, filename: str) -> tuple[float, list[str]]:
    """Heuristically score whether a Gmail message likely contains a real resume."""
    score = 0.0
    reasons = []

    subject_l = (subject or "").lower()
    sender_l = (sender or "").lower()
    snippet_l = (snippet or "").lower()
    filename_l = (filename or "").lower()

    for keyword in POSITIVE_KEYWORDS:
        if keyword in subject_l:
            score += 2.0
            reasons.append(f"subject:{keyword}")
        if keyword in snippet_l:
            score += 1.0
            reasons.append(f"snippet:{keyword}")
        if keyword in filename_l:
            score += 2.0
            reasons.append(f"filename:{keyword}")

    for keyword in NEGATIVE_KEYWORDS:
        if keyword in subject_l:
            score -= 2.0
            reasons.append(f"subject_not_resume:{keyword}")
        if keyword in snippet_l:
            score -= 1.0
            reasons.append(f"snippet_not_resume:{keyword}")
        if keyword in filename_l:
            score -= 2.0
            reasons.append(f"filename_not_resume:{keyword}")

    # Recruiting mailbox names are weak but useful hints when content is ambiguous.
    if any(term in sender_l for term in ("recruit", "talent", "hiring", "careers", "jobs@")):
        score += 1.5
        reasons.append("sender:recruiting_hint")

    return score, reasons


def _iter_message_parts(parts: list[dict]) -> list[dict]:
    """Flatten nested Gmail MIME parts so attachments are easy to inspect."""
    flattened = []
    stack = list(parts)
    while stack:
        part = stack.pop()
        flattened.append(part)
        stack.extend(part.get("parts", []))
    return flattened


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        # Reuse a saved OAuth token when possible to avoid prompting every run.
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Local OAuth flow is acceptable here because this project currently
            # targets developer-operated ingestion rather than headless automation.
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as file_obj:
            file_obj.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_emails_with_attachments(service, max_results: int = 5) -> list:
    """Search Gmail for candidate emails matching the configured attachment query."""
    results = service.users().messages().list(
        userId="me",
        q=GMAIL_QUERY,
        maxResults=max_results,
    ).execute()
    return results.get("messages", [])


def download_pdf_attachment(service, message_id: str) -> tuple[str | None, str, str, str, str, float, list[str]]:
    """
    Download PDF attachment from an email.
    Returns (file_path, sender_email, subject, filename, snippet, score, reasons).
    """
    # Pull the full MIME payload because Gmail stores attachments on nested parts.
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()

    headers = message.get("payload", {}).get("headers", [])
    sender = next((h["value"] for h in headers if h["name"] == "From"), "")
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
    snippet = message.get("snippet", "")

    parts = _iter_message_parts(message.get("payload", {}).get("parts", []))
    for part in parts:
        filename = part.get("filename", "")
        mimetype = part.get("mimeType", "")

        if "pdf" in mimetype.lower() or filename.lower().endswith(".pdf"):
            attachment_id = part.get("body", {}).get("attachmentId")
            if not attachment_id:
                continue

            attachment = service.users().messages().attachments().get(
                userId="me", messageId=message_id, id=attachment_id
            ).execute()
            data = base64.urlsafe_b64decode(attachment["data"])
            score, reasons = _score_resume_likelihood(subject, sender, snippet, filename)

            # Write to a temp file because the existing resume parser expects a path.
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="gmail_resume_")
            tmp.write(data)
            tmp.close()
            return tmp.name, sender, subject, filename, snippet, score, reasons

    return None, sender, subject, "", snippet, -999.0, ["no_pdf_attachment"]


def fetch_all_gmail_candidates() -> list[dict]:
    """Main function - returns parsed candidates from Gmail attachments."""
    print("Connecting to Gmail...")
    service = get_gmail_service()

    print("Searching for emails with PDF attachments...")
    messages = get_emails_with_attachments(service, max_results=10)
    print(f"Found {len(messages)} emails with PDFs")

    candidates = []
    for msg in messages:
        message_id = msg["id"]
        print(f"Processing email {message_id}...")

        pdf_path, sender, subject, filename, snippet, score, reasons = download_pdf_attachment(service, message_id)
        if not pdf_path:
            print(f"No PDF found in email {message_id} - skipping")
            continue

        # Heuristic filtering avoids wasting extraction calls on invoices/brochures.
        if score < RESUME_SCORE_THRESHOLD:
            print(
                f"Skipping email {message_id} - resume score {score:.1f} below threshold "
                f"{RESUME_SCORE_THRESHOLD:.1f}. filename={filename!r} subject={subject!r} reasons={reasons}"
            )
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
            continue

        try:
            data = parse_resume(pdf_path)

            # When the resume omits an email address, fall back to the sender address.
            if not data.get("email") and sender:
                match = re.search(r"[\w.-]+@[\w.-]+", sender)
                if match:
                    data["email"] = match.group(0)

            data["source"] = "gmail"
            data["source_metadata"] = data.get("source_metadata", {})
            # Preserve Gmail-specific audit details separately from the main candidate fields.
            data["source_metadata"]["gmail_message_id"] = message_id
            data["source_metadata"]["email_subject"] = subject
            data["source_metadata"]["sender"] = sender
            data["source_metadata"]["attachment_filename"] = filename
            data["source_metadata"]["gmail_snippet"] = snippet
            data["source_metadata"]["resume_score"] = score
            data["source_metadata"]["resume_score_reasons"] = reasons

            if data.get("name"):
                candidates.append(data)
                print(f"Parsed: {data.get('name')} from {sender}")
            else:
                print(f"Could not extract name from email {message_id} - skipping")

        except Exception as exc:  # noqa: BLE001
            print(f"Failed to parse PDF from email {message_id}: {exc}")

        finally:
            # Always clean up temporary PDFs so repeated syncs do not leak files.
            if pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)

    return candidates

