# Authentication — Usage Cheat Sheet (Appendix for API Documentation)

> Scope: This appendix standardizes client interaction with authentication endpoints and clarifies body vs. header usage.

## Overview

Authentication uses **JSON Web Tokens (JWT)** signed with HS256. Tokens are returned by the login endpoint and presented on protected routes via the **Authorization** header using the **Bearer** scheme.

---

## Endpoint Patterns

| Endpoint             | Method | Request Body                                     | Auth Header                   | Response (200)                                       |
| -------------------- | ------ | ------------------------------------------------ | ----------------------------- | ---------------------------------------------------- |
| `/api/v1/auth/login` | POST   | JSON: `{ "username": "str", "password": "str" }` | _None_                        | `{ "access_token": "jwt", "token_type": "bearer" }`  |
| `/api/v1/auth/me`    | GET    | _None_                                           | `Authorization: Bearer <jwt>` | `{ "id": int, "username": "str", "is_admin": bool }` |

_**Notes**_

- `/auth/me` ignores any request body; authorization is derived exclusively from the `Authorization` header.
- Token expiry and algorithm are configured in server settings.

---

## Request/Response Examples

### Login

_**Request**_

```http
POST /api/v1/auth/login
Content-Type: application/json

{ "username": "brice", "password": "secret123" }
```

_**Response**_

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

### Me (WhoAmI)

_**Request**_

```http
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOi...
```

_**Response**_

```json
{ "id": 1, "username": "brice", "is_admin": false }
```

---

## Curl Sanity

```bash
# Obtain a token
TOKEN=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/login   -H "Content-Type: application/json"   -d '{"username":"brice","password":"secret123"}' | jq -r .access_token)

# Use the token
curl -sS http://127.0.0.1:8000/api/v1/auth/me   -H "Authorization: Bearer $TOKEN"
```

---

## Client Setup (Insomnia/Postman)

**Store token from login response (pseudo-tests snippet):**

```js
// Parse response JSON and save token to an environment variable named "access_token"
const body = JSON.parse(response.body);
pm.environment.set("access_token", body.access_token);
```

**Apply token on protected requests:**

```json
{
  "Authorization": "Bearer {{ access_token }}"
}
```

_**Common mistakes**_

- Sending JSON to `/auth/me`. The endpoint reads `Authorization: Bearer` only.
- Including quotes around the token (`Bearer "ey..."`) or passing an empty variable (becomes `Bearer null`).
- Using mismatched token between requests due to an out-of-date environment variable.

---

## 401 Unauthorized — Diagnostic Guide

| Detail message          | Likely cause                            | Action                                                        |
| ----------------------- | --------------------------------------- | ------------------------------------------------------------- |
| `Invalid credentials`   | Username not found or password mismatch | Validate inputs; confirm hashing method on server.            |
| `Invalid token`         | Signature mismatch or corrupted token   | Ensure same secret/algorithm for encode/decode; resend token. |
| `Token expired`         | Token beyond configured expiry          | Re-authenticate (login) to obtain a new token.                |
| `Invalid token payload` | Missing `sub` or malformed claims       | Verify token creation sets `sub` and standard claims.         |

---
