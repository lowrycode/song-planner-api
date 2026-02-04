
import os
import time
from google import genai
from google.genai import types

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

EMBED_MODEL = os.getenv("EMBED_MODEL")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS"))
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1  # initial wait time


class EmbeddingServiceUnavailable(Exception):
    pass


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Makes API call to Gemini embedding model with retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="SEMANTIC_SIMILARITY",
                    output_dimensionality=EMBED_DIMENSIONS,
                ),
            )

            if not result.embeddings:
                raise EmbeddingServiceUnavailable("No embeddings returned")

            embeddings = [embedding.values for embedding in result.embeddings]

            # Validate dimensionality
            for emb in embeddings:
                if not emb or len(emb) != EMBED_DIMENSIONS:
                    raise EmbeddingServiceUnavailable("Invalid embedding shape")

            return embeddings  # success - return early

        except Exception as exc:
            # Log failure with attempt count
            print(f"Attempt {attempt} failed: {exc}")

            if attempt == MAX_RETRIES:
                print("Max retries reached. Raising EmbeddingServiceUnavailable.")
                raise EmbeddingServiceUnavailable() from exc

            # Exponential backoff delay before next retry
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            print(f"Retrying after {delay} seconds...")
            time.sleep(delay)
