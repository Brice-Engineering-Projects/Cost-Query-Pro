# Architecture Overview

---

## Project Name

**Unit Cost Query App for Infrastructure Projects**

---

## Purpose

This document describes the high-level architecture of the Unit Cost Query App. It explains how system components fit together and how data flows through the application. The goal is to help developers, architects, and stakeholders quickly understand the system design.

---

## System Overview

The app consists of:

- **Frontend UI** — allows users to:
  - Upload data files
  - Search historical unit costs
  - Manage data (admins only)

- **Backend API** — handles:
  - File ingestion and data transformation
  - Database operations
  - User authentication
  - Query processing

- **Database** — stores:
  - Projects and item details
  - User accounts and permissions

- **PDF Parsing Tools** — extract tables from PDF bid tab sheets

---

## High-Level Architecture Diagram

Here’s an ASCII-style diagram for clarity (replace with a visual diagram later if desired):

┌───────────────┐
│ Frontend │
│ (Web UI / JS) │
└──────┬────────┘
│
│ HTTP Requests
│
┌──────▼────────┐
│ FastAPI │
│ Backend │
└──────┬────────┘
│
│ SQLAlchemy
│
┌──────▼────────┐
│ PostgreSQL DB │
└───────────────┘


---

## Component Descriptions

### 1. Frontend UI

**Purpose:** User interface for data upload, search, and admin functions.

**Possible Technologies:**

- Jinja2 templates (simple HTML)
- OR modern JS frameworks:
  - React
  - Vue
  - Streamlit (rapid prototypes)

**Key Features:**

- Upload form for Excel/CSV/PDF
- Search form with filters (item name, state, year)
- Results table displaying matching unit costs
- Admin dashboard for:
  - User management
  - Data purging

---

### 2. FastAPI Backend

**Purpose:** Handles all server-side logic and data processing.

**Responsibilities:**

- Expose REST API endpoints
- Authenticate users
- Process uploaded files
- Transform and load data into the DB
- Execute search queries

**Key Technologies:**

- Python
- FastAPI
- SQLAlchemy ORM
- pdfplumber or tabula-py (for PDF parsing)
- pandas (data cleaning)

---

### 3. Database (PostgreSQL)

**Purpose:** Persistently store structured data.

**Tables:**

- `projects`
  - Project ID
  - Project Name
  - Project Number
  - State
  - Year

- `items`
  - Item ID
  - Project ID (foreign key)
  - Item Description
  - Unit
  - Unit Price

- `users`
  - User ID
  - Username
  - Password hash
  - Is_Admin (boolean)

**Relationships:**

- One project → many items

---

### 4. PDF Parsing Tools

**Purpose:** Extract tabular data from PDF bid tabulations.

**Tools:**

- pdfplumber
- OR tabula-py

**Considerations:**

- Some PDFs may be inconsistently formatted
- Manual intervention might be required for complex layouts

---

## Data Flow Example

Here’s an example of how data moves through the system:

### Upload Workflow

1. User logs in.
2. User uploads a CSV, Excel, or PDF.
3. Backend:
   - Reads file into pandas DataFrame
   - Cleans and standardizes data
   - Checks for duplicate projects
   - Stores data into PostgreSQL tables
4. User sees confirmation of successful upload.

---

### Search Workflow

1. User logs in.
2. User enters a search term (e.g. “PVC Pipe”) and filters (state, year range).
3. Frontend sends API request to backend.
4. Backend:
   - Builds SQL query
   - Fetches matching records
5. Backend returns:
   - Item description
   - Unit
   - Unit price
   - Project details
6. Frontend displays results in a table.

---

## Security Considerations

- All user actions require authentication.
- Passwords stored as secure hashes.
- Admin-only routes:
  - Purging old data
  - User management
- HTTPS recommended for deployment.
- Input sanitization and validation for:
  - Uploads
  - Search terms

---

## Scalability & Future Enhancements

- Database indexes for faster queries on large datasets.
- Pagination in search results.
- Possible caching for frequently searched items.
- Potential move to cloud services (AWS, GCP, Azure) for:
  - Scalable storage
  - Managed databases
- Data visualization layer for:
  - Cost trends over time
  - Geospatial mapping

---

## Diagram To-Do

✅ Replace ASCII diagram above with a real diagram in the future:

- [ ] System diagram (Lucidchart, draw.io, etc.)
- [ ] Database ERD

---

## TL;DR

The Unit Cost Query App architecture is:

- Frontend → FastAPI backend → PostgreSQL database
- Handles uploads, cleaning, and search
- Designed for maintainability, security, and future scaling

Your cost data’s new best friend!
