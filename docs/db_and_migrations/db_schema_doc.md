# Database Schema Documentation

---

## Project Name

**Unit Cost Query App for Infrastructure Projects**

---

## Purpose

This document defines the relational database schema for the Unit Cost Query App. It covers tables, fields, data types, constraints, and relationships between tables.

This ensures consistency across development, future migrations, and data integrations.

---

## Database System

- **Engine:** PostgreSQL
- **ORM:** SQLAlchemy

---

## Database Tables

---

## 1. Projects Table

**Table Name:** `projects`

Stores high-level details for infrastructure projects.

| Column Name     | Data Type | Constraints           | Description                          |
|-----------------|-----------|-----------------------|--------------------------------------|
| id              | SERIAL    | PRIMARY KEY           | Unique identifier for each project   |
| project_name    | TEXT      | NOT NULL              | Name of the project                  |
| project_number  | TEXT      | UNIQUE, NOT NULL      | Official project reference number    |
| state           | VARCHAR(2)| NOT NULL              | U.S. state abbreviation (e.g. FL)    |
| year            | INTEGER   | CHECK (> 1900)        | Year the project was bid or built    |

---

## 2. Items Table

**Table Name:** `items`

Stores details of each bid item tied to a specific project.

| Column Name       | Data Type | Constraints           | Description                       |
|-------------------|-----------|-----------------------|-----------------------------------|
| id                | SERIAL    | PRIMARY KEY           | Unique identifier for each item   |
| project_id        | INTEGER   | FOREIGN KEY → projects.id, NOT NULL | Links item to its project |
| item_description  | TEXT      | NOT NULL              | Description of the bid item       |
| unit              | TEXT      | NOT NULL              | Unit of measurement (e.g. LF, EA) |
| unit_price        | NUMERIC(12, 2) | NOT NULL        | Unit cost (e.g. 45.32)            |

---

## 3. Users Table

**Table Name:** `users`

Stores app users for authentication and authorization.

| Column Name   | Data Type | Constraints          | Description                       |
|---------------|-----------|----------------------|-----------------------------------|
| id            | SERIAL    | PRIMARY KEY          | Unique user identifier            |
| username      | TEXT      | UNIQUE, NOT NULL     | User login name                   |
| password_hash | TEXT      | NOT NULL             | Secure hash of user’s password    |
| is_admin      | BOOLEAN   | DEFAULT FALSE        | True if user has admin privileges |

---

## Relationships

- **projects → items:**
  - One-to-many relationship
  - One project can have multiple items
  - Enforced by `project_id` foreign key in `items`

- **users:**
  - Currently independent of other tables
  - Used for authentication and authorization only

---

## Data Types & Constraints Explained

- **SERIAL**: Auto-incrementing integer for primary keys.
- **TEXT**: For variable-length text data.
- **VARCHAR(2)**: Two-character strings (e.g. state codes).
- **INTEGER**: Numeric values without decimals.
- **NUMERIC(12, 2)**: Fixed-precision decimals for currency (e.g. unit price).
- **BOOLEAN**: True/False values.

---

## Example SQL Statements

### Create `projects` Table

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    project_name TEXT NOT NULL,
    project_number TEXT UNIQUE NOT NULL,
    state VARCHAR(2) NOT NULL,
    year INTEGER CHECK (year > 1900)
);
```

---

### Create `items` Table

```sql
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    item_description TEXT NOT NULL,
    unit TEXT NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL
);
```

---

### Create `user` Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE
);
```

---

### Future Considerations

- Add audit tables for:
- Data purging logs
- Upload history
- Add timestamp columns (e.g. created_at, updated_at) for better tracking.
- Consider table partitioning for large datasets in items.
- Explore indexing strategies for:
- Frequent search fields (item_description, state, year)
