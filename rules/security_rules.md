# TIDOS Security Rules & Invariants (v3.0)

TIDOS enforces zero-trust security invariants across all software projects:

---

## 1. Zero-Trust Input Sanitization
- Treat all incoming user inputs, route parameters, and third-party API payloads as untrusted.
- Validate payloads using strongly-typed schemas (Zod, Pydantic, typed DTOs) at application entry boundaries.

## 2. Absolute Secret Isolation
- Never hardcode secrets, API keys, passwords, private keys, or tokens in source code files or Git repositories.
- Load environment variables from `.env` files or secure Key Vaults via strongly-typed config schemas.
- Exclude secrets using `.gitignore` and `.dockerignore`.

## 3. Database & Row Level Security (RLS)
- Enforce Row Level Security (RLS) on **every** Supabase / PostgreSQL table without exception.
- Enforce strict ownership and authentication checks in Firebase `firestore.rules` and `storage.rules`. Never deploy wildcard `allow read, write: if true;` rules.

## 4. Log Protection & Least Privilege
- Never write credentials, auth tokens, passwords, or PII (Personally Identifiable Information) to log outputs.
- Restrict API permissions, database user roles, and storage buckets to minimum required execution bounds.
