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

EMBED_MODEL = os.getenv("EMBED_MODEL")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS"))
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1  # initial wait time


class EmbeddingServiceUnavailable(Exception):
    pass


gemini_retry_strategy = retry(
    reraise=True,
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=BASE_DELAY_SECONDS, min=1, max=60),
    retry=retry_if_exception_type(
        (errors.APIError, errors.ClientError, EmbeddingServiceUnavailable)
    ),
)


@gemini_retry_strategy
def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Makes API call to Gemini embedding model. Tenacity handles retries."""
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=EMBED_DIMENSIONS,
        ),
    )

    if not result or not result.embeddings:
        raise EmbeddingServiceUnavailable("No embeddings returned")

    embeddings = [embedding.values for embedding in result.embeddings]

    # Validate dimensionality
    for emb in embeddings:
        if not emb or len(emb) != EMBED_DIMENSIONS:
            raise EmbeddingServiceUnavailable("Invalid embedding shape")

    return embeddings
