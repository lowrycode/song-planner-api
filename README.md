# Song Planner Dashboard — Backend API

A secure **REST API** powering the **Song Planner Dashboard**. It handles authentication, authorisation, song usage analytics, and data aggregation across a network of churches.

The API also integrates **third-party LLM services** to generate thematic summaries for songs and Bible passages, and implements a **Retrieval-Augmented Generation (RAG)** pipeline using vector embeddings to enable semantic song search.

## Related repository:  

👉 **Frontend (React + TypeScript):**
https://github.com/lowrycode/song-planner-dashboard

## Overview

This backend provides the core business logic and data access layer for the Song Planner Dashboard. It manages:
- Users, roles, and permissions
- Networks, churches, and activities
- Songs, lyrics, and related resources
- Song usage records and aggregated usage statistics
- Semantic search infrastructure and AI-assisted content analysis

A key design goal of the API is to **enforce access control and data restrictions server-side**, ensuring users can only query data they are explicitly permitted to see.

## Tech Stack

- **FastAPI**: High-performance REST API framework
- **Pydantic / pydantic-settings**: Request validation and configuration
- **SQLAlchemy ORM**: Database access and query composition
- **PostgreSQL**: Primary relational database
- **pgvector**: PostgreSQL extension enabling vector similarity searches
- **Alembic**: Database migrations (used earlier in development; schema later reset)
- **Gemini Models**: Theme summarisation and embedding generation
- **External Bible API**: Retrieval of scripture text for thematic analysis
- **JWT (python-jose / pyjwt)**: Authentication tokens
- **Argon2 + bcrypt**: Secure password hashing
- **pytest + httpx**: Test-driven development and API testing
- **Gunicorn**: Production application server
- **Google Cloud Run**: Backend hosting
- **Render**: Backend hosting (in development)

## Authentication & Authorisation

### Authentication

- Users authenticate via username and password.
- **JWT access tokens** are issued for short-lived authentication.
- **Refresh tokens** are stored server-side, hashed in the database.
- Tokens are sent via **HTTP-only cookies** for improved security.
- Refresh tokens **rotate on use**, and can be revoked explicitly.

This approach improves security by reducing XSS exposure, enabling server-side session invalidation, and aligning with modern browser cookie constraints.


### Authorisation

Authorisation is enforced consistently using **FastAPI dependencies**, ensuring protected logic is applied before queries are executed.

Checks include:
- User authentication
- Minimum required role (e.g. admin-only endpoints)
- Resource-scoped permissions (network, church, activity)

Common enforcement pattern:
- Authenticate user
- Verify minimum role
- Compute allowed resource IDs
- Restrict database queries to those IDs

This guarantees users **cannot infer or access data** outside their permitted scope.

### Permission Model

The permission model is intentionally **fine-grained** and data-driven.
- Users belong to a single network and church
- Additional access is granted through join tables:
  - UserNetworkAccess
  - UserChurchAccess
  - UserChurchActivityAccess
- Permissions are evaluated centrally and reused across endpoints
- No frontend-only permission logic is relied upon

This design allows administrators to control access **without duplicating logic** across API endpoints.

## Data Model Overview

Core domain entities include:
- **User:** Authentication, role, and identity
- **Network / Church / ChurchActivity:** Organisational hierarchy
- **Song:** Metadata (key, type, duration, author)
- **SongUsage:** Individual usage events
- **SongUsageStats:** Pre-aggregated first/last usage per activity
- **SongLyrics / SongResources:** Extended song content
- **SongThemes:** Generated from lyrics using LLM
- **SongLyricEmbeddings / SongThemeEmbeddings:** Vector representations of lyrics and themes used for semantic similarity search.

A dedicated `SongUsageStats` table is used to:
- Optimise analytics queries
- Avoid repeated aggregation over large usage datasets
- Support efficient filtering by date range and activity
- Strategic indexing and unique constraints are applied to support query performance and data integrity

## API Design & Query Strategy

The API follows **RESTful conventions**.

Key characteristics:
- Server-side filtering by date range, activity, song attributes, and permissions
- Aggregation-heavy endpoints to minimise frontend processing
- Use of outer joins to include unused or newly introduced songs
- Consistent response models defined via Pydantic

Complex analytics logic is intentionally handled in the backend, keeping the frontend lightweight and focused on presentation.

## AI-Powered Semantic Search & Content Analysis

The backend implements **Retrieval-Augmented Generation (RAG)** to enable semantic song discovery and automated thematic analysis.

### Semantic Song Search

Semantic search allows songs to be retrieved based on lyrical meaning or thematic similarity rather than exact keyword matches.

This is achieved by:
- Generating theme summaries for songs using large language models
- Generating vector embeddings for:
  - Song lyrics
  - Generated song theme summaries
- Storing embeddings using the PostgreSQL pgvector extension
- Performing similarity searches using vector distance queries

This allows users to discover songs based on conceptual similarity, rather than keyword matches.

### Bible Passage Theme Extraction

The API integrates with an external Bible API to retrieve passage text. The retrieved content is processed using generative AI models to:
- Extract thematic summaries from Bible passages
- Generate embeddings for those summaries
- Enable similarity matching between Bible themes and song themes

This allows users to identify songs aligned with specific scriptural themes.

### AI Models

The system uses Gemini models for:
- Theme summarisation
- Embedding generation

AI processing is performed server-side to maintain consistency, auditability, permission enforcement, and to ensure third-party API credentials remain secure and are never exposed to the client.

## Testing Strategy

Many of the endpoints were developed using **test-driven development (TDD)** principles.
- **pytest** is used as the test framework
- **httpx** is used for API-level request testing

Tests focus on:
- Authentication and authorisation correctness
- Permission boundaries
- Query filtering and aggregation logic

This approach helped validate complex access rules early in development.

## Environment & Configuration

Configuration is managed via environment variables. During local development, these are typically stored in a `.env` file which should not be committed to the repository.

```bash
# Database
DB_URL=<database_url>
TEST_DB_URL=<test_database_url>

# Security
SECRET_KEY=<used_for_tokens>
IS_DEV=True  # Adjusts HTTP-only cookie security and SameSite behaviour
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:4173

# Google Gemini Models
GEMINI_API_KEY=<google_api_key>
EMBED_MODEL=gemini-embedding-001
EMBED_DIMENSIONS=768
GEN_SUMMARY_MODEL=gemini-2.5-flash-lite

# Bible API
API_BIBLE_URL=<bible_api_url>
API_BIBLE_TOKEN=<bible_api_key>
```

No secrets are committed to the repository.

## Local Development

To avoid package conflicts, install dependencies in a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To run the app:
```bash
uvicorn app.main:app --reload
```

**Recommended:** Python 3.12

A PostgreSQL database is required for local development. This could be installed locally or deployed in the cloud (e.g. Neon).

The database requires the `pgvector` extension to support semantic search embeddings. During local development, I used a PostgreSQL Docker container with pgvector pre-installed.

If using a different PostgreSQL instance, run the following SQL to enable the extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```


## Planned Improvements

- Introduce Redis caching for frequently requested analytics queries, AI-generated summaries, and external Bible API responses
