"""
schemas.py — Pydantic schemas untuk API request/response.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MaskRequest(BaseModel):
    """Request body untuk endpoint POST /mask-text."""

    content: str = Field(
        ...,
        description="Teks markdown yang akan di-mask.",
        min_length=1,
    )


class MaskResponse(BaseModel):
    """Response body dari endpoint POST /mask-text."""

    content: str = Field(
        ...,
        description="Teks markdown setelah masking.",
    )
