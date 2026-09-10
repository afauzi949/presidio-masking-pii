"""
main.py — FastAPI application untuk presidio-masking-service.

Endpoint:
    POST /mask-text
        Request:  { "content": "<markdown string>" }
        Response: { "content": "<markdown string ter-masking>" }

Jalankan dengan:
    uvicorn src.api.main:app --reload --port 8001
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import MaskRequest, MaskResponse
from src.masker import mask_document

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Presidio Free-Text Masking Service",
    description=(
        "Service masking untuk konten free-text / unstructured (mis. dokumen Confluence "
        "yang sudah dikonversi ke markdown). Menggunakan Presidio Analyzer + custom "
        "credential recognizer. Masking terjadi sebelum tahap chunking/embedding."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "presidio-masking-service"}


@app.post("/mask-text", response_model=MaskResponse, tags=["masking"])
def mask_text(body: MaskRequest) -> MaskResponse:
    """
    Mask teks markdown: deteksi dan anonimkan entitas PII + kredensial teknis.

    - Dokumen disegmentasi per tipe elemen (prose, code block, tabel).
    - Tiap segmen diproses oleh handler yang sesuai.
    - Output tetap valid markdown untuk tahap chunking/embedding berikutnya.
    """
    try:
        masked = mask_document(body.content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Masking failed: {exc}") from exc

    return MaskResponse(content=masked)
