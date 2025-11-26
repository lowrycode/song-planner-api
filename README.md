# Building an Authentication System

1. Database Tables
- Docker Desktop
- Create Database with PostgreSQL
- Define Models: user, refresh_tokens
- Create database tables: using ORM

2. FastAPI main.py
- CORS Middleware
- Router for auth

3. POST /register (in auth router)
  - Schema-In: UserRegister with password validation
  - check username not already in database
  - hash password
  - create user

4. POST /login (in auth router)