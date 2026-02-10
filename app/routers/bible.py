import re
import httpx
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from app.dependencies import require_min_role
from app.schemas.bible import (
    BiblePassageRequest,
    BiblePassageResponse,
    GenerateThemesRequest,
    GenerateThemesResponse,
)
from app.models import UserRole, User
from app.settings import settings
from app.utils.rag import generate_themes_from_bible_text, ExternalServiceError


router = APIRouter()


@router.get(
    "",
    response_model=BiblePassageResponse,
    tags=["bible"],
    summary="Retrieve Bible passage",
)
async def bible_passage(
    query: Annotated[BiblePassageRequest, Query()],
    user: User = Depends(require_min_role(UserRole.normal)),
):
    params = {
        "q": query.ref,
        "indent-poetry": False,
        "include-headings": False,
        "include-footnotes": False,
        "include-verse-numbers": False,
        "include-short-copyright": False,
        "include-passage-references": False,
    }

    headers = {"Authorization": f"Token {settings.API_BIBLE_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                settings.API_BIBLE_URL, params=params, headers=headers
            )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Bible service unavailable")

    if response.status_code == 404:
        raise HTTPException(404, "Passage not found")

    if not response.is_success:
        raise HTTPException(502, "Bible API request failed")
    data = response.json()

    try:
        raw_text = data["passages"][0]
    except (KeyError, IndexError):
        raise HTTPException(status_code=404, detail="Passage not found")

    text = re.sub(r"\s+", " ", raw_text).strip()

    return BiblePassageResponse(text=text)


@router.post(
    "/themes",
    response_model=GenerateThemesResponse,
    tags=["bible"],
    summary="Generate themes from Bible text",
)
def generate_bible_themes(
    body: GenerateThemesRequest,
    user: User = Depends(require_min_role(UserRole.normal)),
):
    try:
        themes = generate_themes_from_bible_text(body.text)
    except ExternalServiceError as exc:
        # Upstream failure → 502 Bad Gateway
        raise HTTPException(status_code=502, detail="Theme generation failed") from exc

    return GenerateThemesResponse(themes=themes)
