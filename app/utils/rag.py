import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from google import genai
from google.genai import types, errors

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

GEN_SUMMARY_MODEL = os.getenv("GEN_SUMMARY_MODEL")
EMBED_MODEL = os.getenv("EMBED_MODEL")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS"))
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1  # initial wait time


class ExternalServiceError(Exception):
    pass


gemini_retry_strategy = retry(
    reraise=True,
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=BASE_DELAY_SECONDS, min=1, max=10),
    retry=retry_if_exception_type(
        (errors.APIError, errors.ClientError, ExternalServiceError)
    ),
)


@gemini_retry_strategy
def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates vector embeddings for a list of text prompts using Gemini
    embedding model. Tenacity handles retries.
    """
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=EMBED_DIMENSIONS,
        ),
    )

    if not result or not result.embeddings:
        raise ExternalServiceError("No embeddings returned")

    embeddings = [embedding.values for embedding in result.embeddings]

    # Validate dimensionality
    for emb in embeddings:
        if not emb or len(emb) != EMBED_DIMENSIONS:
            raise ExternalServiceError("Invalid embedding shape")

    return embeddings


@gemini_retry_strategy
def generate_themes_from_bible_text(text: str):
    """Generates theme summary from Bible text using Gemini generation model"""
    contents = f"""
Extract the following from the Bible text below:

Spiritual themes: 3 to 6 short descriptive phrases, comma-separated on a single line
Emotional tone: 2 to 4 adjectives or short phrases, comma-separated on a single line
Theological ideas: 2 to 4 concrete theological concepts, comma-separated on a single
line

Write each category label.
Do not use bullet points or line breaks within each category.
Do not write full sentences. Avoid speculation.

Bible text:
{text}
"""
    try:
        response = client.models.generate_content(
            model=GEN_SUMMARY_MODEL,
            contents=contents,
        )
    except (errors.APIError, errors.ClientError) as e:
        raise ExternalServiceError(str(e))

    if not response or not response.text:
        raise ExternalServiceError("No response from Gemini")

    return response.text.strip()
