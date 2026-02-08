# Cost Query Pro – API Reference

---

## Project Name

_**Cost Query Pro**_

---

## Purpose

This document describes the REST API endpoints provided by the Cost Query Pro backend. It defines how frontend applications and external tools can interact with the system.

---

## Base URL

```bash
/api/v1/
```

_*(Adjust if deploying behind a reverse proxy or custom domain.)*_

---

## Authentication

All endpoints require authentication unless explicitly marked as public.

**Authentication Method:**

- HTTP Bearer Token (JWT recommended)

Example header:

```json
{
  "Authorization": "Bearer <your-token-here>"
}
```

---

## Endpoints

---

## 1. User Authentication

---

### POST `/auth/login`

**Purpose:** Authenticate a user and return an auth token.

**Request:**

```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response (success):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI...",
  "token_type": "bearer"
}
```

**Response (failure):**

```json
{
  "detail": "Invalid username or password"
}
```

---

### POST `/auth/register`

_*(Optional, depending on how user creation is managed. Could be admin-only.)*_

**Purpose:** Create a new user account.

**Request:**

```json
{
  "username": "new_user",
  "password": "password123",
  "is_admin": false
}
```

**Response (success):**

```json
{
  "message": "User created successfully."
}
```

---

## 2. Project Data Upload

---

### POST `/projects/upload`

**Purpose:** Upload a file (CSV, Excel, PDF) for ingestion into the database.

**Headers:**

```json
{
  "Content-Type": "multipart/form-data"
}
```

**Form fields:**

- `file`: The uploaded file (PDF, CSV, or XLSX)

**Response (success):**

```json
{
  "message": "File uploaded and processed successfully.",
  "records_inserted": 123
}
```

**Response (failure):**

```json
{
  "error": "Unsupported file type."
}
```

---

## 3. Search Unit Costs

---

### GET `/items/search`

**Purpose:** Search historical unit costs by keyword, state, and year range.

**Query Parameters:**

| Parameter       | Type     | Required | Description                        |
|-----------------|----------|----------|------------------------------------|
| q               | string   | Yes      | Search term (e.g. "PVC Pipe")      |
| state           | string   | No       | Two-letter state code (e.g. FL)    |
| year_start      | integer  | No       | Starting year of search range      |
| year_end        | integer  | No       | Ending year of search range        |

**Example Request:**

```bash
/api/v1/items/search?q=PVC+Pipe&state=FL&year_start=2022&year_end=2024
```

**Response:**

```json
[
  {
    "item_description": "8\" PVC Gravity Sewer",
    "unit": "LF",
    "unit_price": 45.32,
    "project_name": "Main St. Sewer Rehab",
    "project_number": "202301",
    "state": "FL",
    "year": 2023
  }
]
```

---

## 4. Admin: Purge Old Data

_*(Admin-only route.)*_

---

### DELETE `/admin/purge`

**Purpose:** Purge projects and items older than a specified year cutoff.

**Request:**

```json
{
  "year_cutoff": 2020
}
```

**Response (success):**

```json
{
  "message": "Data older than 2020 has been purged.",
  "projects_deleted": 17,
  "items_deleted": 623
}
```

---

## 5. Admin: User Management

_*(Admin-only routes.)*_

---

### GET `/admin/users`

**Purpose:** Retrieve a list of all users.

**Response:**

```json
[
  {
    "id": 1,
    "username": "john_doe",
    "is_admin": true
  },
  {
    "id": 2,
    "username": "jane_smith",
    "is_admin": false
  }
]
```

---

### DELETE `/admin/users/{user_id}`

**Purpose:** Delete a user by ID.

**Response:**

```json
{
  "message": "User deleted successfully."
}
```

---

## Standard Response Codes

| Status Code | Meaning                      |
|-------------|------------------------------|
| 200         | OK                           |
| 201         | Created                      |
| 400         | Bad Request                  |
| 401         | Unauthorized                 |
| 403         | Forbidden                    |
| 404         | Not Found                    |
| 409         | Conflict (e.g. duplicate)    |
| 500         | Internal Server Error        |

---

## Future API Enhancements

- Pagination for search results
- CSV/Excel export endpoints
- Detailed logging endpoints
- Versioning beyond `/v1/`

---

## TL;DR

The Cost Query Pro API provides:

- User authentication and tokens
- File upload for cost data
- Powerful search for historical unit costs
- Admin tools for purging and user management

Secure, organized, and ready for action!
