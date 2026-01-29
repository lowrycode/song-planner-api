# Song Planner Dashboard — Backend API

A secure **REST API** powering the **Song Planner Dashboard**, responsible for authentication, authorisation, data aggregation, and analytics over song usage data across a network of churches.

## Related repository:  

👉 **Frontend (React + TypeScript):**
https://github.com/lowrycode/song-planner-dashboard

## Overview

This backend provides the core business logic and data access layer for the Song Planner Dashboard. It manages:
- Users, roles, and permissions
- Networks, churches, and activities
- Songs, lyrics, and related resources
- Song usage records and aggregated usage statistics

A key design goal of the API is to **enforce access control and data restrictions server-side**, ensuring users can only query data they are explicitly permitted to see.

## Tech Stack

- **FastAPI**: High-performance REST API framework
- **SQLAlchemy ORM**: Database access and query composition
- **PostgreSQL**: Primary relational database
- **Pydantic / pydantic-settings**: Request validation and configuration
- **JWT (python-jose / pyjwt)**: Authentication tokens
- **Argon2 + bcrypt**: Secure password hashing
- **Alembic**: Database migrations (used earlier in development; schema later reset)
- **Gunicorn**: Production application server
- **Render**: Backend hosting
- **pytest + httpx**: Test-driven development and API testing

## Authentication & Authorisation

### Authentication

- Users authenticate via username and password.
- **JWT access tokens** are issued for short-lived authentication.
- **Refresh tokens** are stored server-side, hashed in the database.
- Tokens are sent via **HTTP-only cookies** for improved security.
- Refresh tokens **rotate on use**, and can be revoked explicitly.

This approach:
- Reduces exposure to XSS attacks
- Allows server-side session invalidation
- Aligns with modern browser security constraints

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

## Testing Strategy

The backend was developed using **test-driven development (TDD)** principles.
- **pytest** is used as the test framework
- **httpx** is used for API-level request testing

Tests focus on:
- Authentication and authorisation correctness
- Permission boundaries
- Query filtering and aggregation logic

This approach helped validate complex access rules early in development.

## Environment & Configuration

Configuration is managed via environment variables.

```bash
DB_URL=<database_url>
TEST_DB_URL=<test_database_url>
SECRET_KEY=<used_for_tokens>
IS_DEV=True
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:4173
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

A PostgreSQL database is required for local development. This could be installed locally (I used a Docker image) or deployed in the cloud (e.g. Neon).

## Planned Improvements

- Semantic and thematic song search (LLM-assisted)