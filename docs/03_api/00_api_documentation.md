# Cost Query Pro – API Reference

---

## Purpose

This document describes the REST API endpoints provided by the Cost Query Pro backend. It is kept in sync with the actual implementation. For auto-generated interactive docs, see `/docs` (Swagger UI) or `/redoc` when the server is running.

---

## Base URL

```
/api/v1/
```

All routes below are relative to this base unless noted otherwise.

---

## Authentication

All endpoints require a valid JWT Bearer token unless explicitly marked as **public**.

```
Authorization: Bearer <access_token>
```

Obtain a token via `POST /api/v1/auth/login` or `POST /api/v1/auth/login-json`.

---

## Standard Response Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error, duplicate, self-action) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient role) |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Unprocessable Entity (Pydantic validation failure) |
| 500 | Internal Server Error |

---

## 1. Authentication

### POST `/auth/login` — OAuth2 form login

**Public.** OAuth2-compatible login using `application/x-www-form-urlencoded`.

**Form fields:** `username`, `password`

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

---

### POST `/auth/login-json` — JSON login

**Public.** Alternative login accepting JSON for API clients.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response:** Same as `/auth/login`.

---

### POST `/auth/register` — Register a new user

**Public.** Accepts either `application/json` or `multipart/form-data`.

**Request (JSON):**
```json
{
  "username": "new_user",
  "password": "password123",
  "is_admin": false
}
```

`is_admin` is only honored when `ALLOW_ADMIN_SIGNUP=true` in settings.

**Response (201):**
```json
{
  "id": 5,
  "username": "new_user",
  "is_admin": false
}
```

**Errors:** `400` if username is already taken or payload is invalid.

---

### GET `/auth/me` — Current user profile

Returns the authenticated user's profile.

**Response:**
```json
{
  "id": 1,
  "username": "john_doe",
  "is_admin": true
}
```

---

## 2. Projects

All project endpoints require authentication.

### POST `/projects/` — Create a project

**Request:**
```json
{
  "project_name": "Main St. Sewer Rehab",
  "project_number": "202301",
  "state": "FL",
  "year": 2023
}
```

**Response (201):**
```json
{
  "id": 10,
  "project_name": "Main St. Sewer Rehab",
  "project_number": "202301",
  "state": "FL",
  "year": 2023
}
```

**Errors:** `400` if `project_number` already exists.

---

### GET `/projects/` — List projects

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| skip | int | Offset (default 0) |
| limit | int | Max results (default 100, max 500) |
| state | string | 2-letter state code filter |
| year | int | Exact year filter |

**Response:** Array of project objects.

---

### GET `/projects/{project_id}` — Get a project

**Response:** Single project object. `404` if not found.

---

### PUT `/projects/{project_id}` — Update a project

**Request:** Any subset of project fields (partial update).

**Response:** Updated project object.

---

### DELETE `/projects/{project_id}` — Delete a project

Deletes the project and all associated items.

**Response:** `204 No Content`

---

### GET `/projects/{project_id}/items` — Get items for a project

**Response:** Array of item objects belonging to the project.

---

## 3. Items

All item endpoints require authentication.

### GET `/items/search` — Search items

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| q | string | Keyword search on `item_description` (case-insensitive) |
| state | string | Filter by project state |
| year_start | int | Filter by project year >= value |
| year_end | int | Filter by project year <= value |
| unit | string | Filter by exact unit type |
| min_price | decimal | Filter by unit_price >= value |
| max_price | decimal | Filter by unit_price <= value |
| skip | int | Offset (default 0) |
| limit | int | Max results (default 100) |

**Response:**
```json
[
  {
    "id": 42,
    "item_description": "8\" PVC Gravity Sewer",
    "unit": "LF",
    "unit_price": 45.32,
    "project_id": 10,
    "project": {
      "id": 10,
      "project_name": "Main St. Sewer Rehab",
      "project_number": "202301",
      "state": "FL",
      "year": 2023
    }
  }
]
```

---

### GET `/items/{item_id}` — Get an item

**Response:** Single item with embedded project. `404` if not found.

---

### POST `/items/` — Create an item

**Request:**
```json
{
  "project_id": 10,
  "item_description": "12\" DIP Water Main",
  "unit": "LF",
  "unit_price": 78.50
}
```

**Response (201):** Created item object. `404` if the referenced project does not exist.

---

### PUT `/items/{item_id}` — Update an item

**Request:** Any subset of item fields (partial update).

**Response:** Updated item object.

---

### DELETE `/items/{item_id}` — Delete an item

**Response:** `204 No Content`

---

### GET `/items/units/distinct` — List distinct unit types

Returns all unique unit values in the database.

**Response:**
```json
["LF", "EA", "SY", "CY", "LS"]
```

---

### GET `/items/stats/price-range` — Price range stats

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| item_query | string | Optional keyword to filter items before computing range |

**Response:**
```json
{
  "min_price": 12.00,
  "max_price": 450.75
}
```

---

## 4. Admin — Data Purge

**Admin-only.**

### DELETE `/admin/purge` — Purge old data

Deletes (and archives) all projects and items with `year < year_cutoff`.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| year_cutoff | int | Yes | Purge all records with year strictly less than this value |

**Response:**
```json
{
  "message": "Data older than 2020 has been purged.",
  "projects_deleted": 17,
  "items_deleted": 623
}
```

---

## 5. Admin — User Management

**Admin-only.** All routes are prefixed `/api/v1/admin/users`.

### GET `/admin/users/` — List all users

**Response:**
```json
[
  { "id": 1, "username": "john_doe", "is_admin": true },
  { "id": 2, "username": "jane_smith", "is_admin": false }
]
```

---

### DELETE `/admin/users/{user_id}` — Delete a user

Admins cannot delete themselves.

**Response:**
```json
{
  "message": "User 'jane_smith' deleted successfully."
}
```

**Errors:** `404` if not found · `400` if attempting self-deletion.

---

### PUT `/admin/users/promote/{user_id}` — Promote user to admin

**Response:** Updated user object with `is_admin: true`.

**Errors:** `404` if not found · `400` if user is already an admin.

---

## 6. AI Agent Query *(Phase 2 — not yet implemented)*

### POST `/agent/query` — Natural language cost query

Accepts a plain-English question and returns a cited answer using the AI agent (Claude primary, OpenAI fallback).

**Request:**
```json
{
  "query": "What is the average cost for a 24-inch jack and bore in Florida?"
}
```

**Response:**
```json
{
  "answer": "Large diameter (24\") jack and bore in Florida averages $285/LF based on 3 project records.",
  "citations": [
    {
      "project_name": "SR-50 Utility Relocation",
      "project_number": "FL-2022-041",
      "source_file": "FL2022_bid_tab.pdf",
      "year": 2022,
      "unit_cost": 280.00,
      "unit": "LF"
    }
  ],
  "provider": "claude",
  "model": "claude-sonnet-4-6"
}
```

Requires JWT authentication. Rate-limited per user.

---

## 7. Health Check

### GET `/` — Health check

**Public.** Returns DB connectivity status.

**Response:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

---

## Planned Enhancements

- Ingest endpoint: `POST /api/v1/ingest/upload` (CSV, Excel, PDF) — Phase 1
- Audit log retrieval endpoint for admin — Phase 2
- CSV/PDF export for search results — Phase 4
- Versioning beyond `/v1/` — Phase 3+
