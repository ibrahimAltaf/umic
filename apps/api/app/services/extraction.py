"""Document text extraction (OCR-lite) from Drive / local bytes."""

from __future__ import annotations

import hashlib
import re
from typing import Optional

import httpx

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

# Google Workspace types we can export as plain text
EXPORTABLE = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

TEXTISH = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
    "text/html",
}


def extract_drive_file_text(client: httpx.Client, access: str, file_meta: dict) -> Optional[str]:
    """Download or export Drive file content as text when feasible."""
    file_id = file_meta.get("id")
    mime = file_meta.get("mimeType") or ""
    if not file_id:
        return None

    headers = {"Authorization": f"Bearer {access}"}
    try:
        if mime in EXPORTABLE:
            resp = client.get(
                f"{DRIVE_FILES_URL}/{file_id}/export",
                params={"mimeType": EXPORTABLE[mime]},
                headers=headers,
                timeout=60.0,
            )
            if resp.status_code >= 400:
                return None
            return _clean_text(resp.text)

        if mime in TEXTISH or mime.startswith("text/"):
            resp = client.get(
                f"{DRIVE_FILES_URL}/{file_id}",
                params={"alt": "media"},
                headers=headers,
                timeout=60.0,
            )
            if resp.status_code >= 400:
                return None
            return _clean_text(resp.text)

        # Lightweight PDF text if pypdf is installed
        if mime == "application/pdf":
            resp = client.get(
                f"{DRIVE_FILES_URL}/{file_id}",
                params={"alt": "media"},
                headers=headers,
                timeout=90.0,
            )
            if resp.status_code >= 400:
                return None
            return extract_pdf_bytes(resp.content)

        if mime.startswith("image/"):
            resp = client.get(
                f"{DRIVE_FILES_URL}/{file_id}",
                params={"alt": "media"},
                headers=headers,
                timeout=90.0,
            )
            if resp.status_code >= 400:
                return None
            return extract_image_bytes(resp.content)
    except Exception:  # noqa: BLE001
        return None
    return None


def extract_pdf_bytes(data: bytes) -> Optional[str]:
    try:
        from pypdf import PdfReader  # type: ignore
        import io

        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages[:40]:
            parts.append(page.extract_text() or "")
        text = _clean_text("\n".join(parts))
        if text:
            return text
        # Scanned PDF pages often have no text layer — OCR first page images if possible
        return extract_pdf_ocr_fallback(data)
    except Exception:  # noqa: BLE001
        return None


def extract_pdf_ocr_fallback(data: bytes) -> Optional[str]:
    """Optional OCR for image-only PDFs when pytesseract + pdf2image available."""
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        import pytesseract  # type: ignore

        images = convert_from_bytes(data, first_page=1, last_page=3)
        parts = [pytesseract.image_to_string(img) for img in images]
        return _clean_text("\n".join(parts))
    except Exception:  # noqa: BLE001
        return None


def extract_image_bytes(data: bytes) -> Optional[str]:
    """OCR a PNG/JPEG when pytesseract is installed."""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        import io

        img = Image.open(io.BytesIO(data))
        return _clean_text(pytesseract.image_to_string(img))
    except Exception:  # noqa: BLE001
        return None


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:50000] if text else ""
