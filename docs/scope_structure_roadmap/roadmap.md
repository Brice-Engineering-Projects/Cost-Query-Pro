# Project Plan – Unit Cost Query App for Infrastructure Projects

---

## 🎯 Problem Statement

In municipal and infrastructure projects, historical **unit costs** for items (e.g. pipes, manholes, paving) are critical for estimating, budgeting, and bid evaluations. However:

- Cost data is scattered across bid tab sheets, PDFs, and Excel files.
- Searching for specific items or prices across multiple projects and years is time-consuming.
- There’s no centralized system to query historical unit prices quickly and reliably.

**Goal:**
Build an application that allows users to search for **unit costs by item, state, and year**, returning the relevant pricing data along with project and source information.

---

## 🗂️ Scope

### Core Functionality

✅ **Upload Data**

- Load bid tab data from Excel, CSV, or PDF into a centralized database.

✅ **Search Capability**

- Search for items by keywords.
- Filter by:
  - State
  - Year range
- Return:
  - Item description
  - Unit
  - Unit price
  - Project name
  - Project number
  - State
  - Year

✅ **Admin Controls**

- Secure login system.
- Admins can:
  - Purge data older than a specified timeframe (e.g. 5 years).
  - Manage user permissions.

✅ **Data Maintenance**

- Ability to delete old data or archive it for storage efficiency.

---

## 🏗️ Recommended Tech Stack

### Backend

- Python
- FastAPI for API and web routes
- SQLAlchemy ORM

### Database

- PostgreSQL for relational data
- SQLAlchemy for model management

### Frontend

Options:

- Jinja2 templates for simple HTML UI
- Or modern frameworks:
  - React
  - Vue
  - Streamlit (for rapid prototyping)

### Other Tools

- pandas for data cleaning and file ingestion
- pdfplumber or tabula-py if extracting tables from PDFs

---

## 🗃️ Database Design

### Tables

#### Projects Table

- Project ID
- Project Name
- Project Number
- State
- Year

#### Items Table

- Item ID
- Project ID (Foreign Key)
- Item Description
- Unit
- Unit Price

#### Users Table (For Authentication)

- User ID
- Username
- Password Hash
- Is_Admin (True/False)

**Relationships:**

- One project can have many items.

---

## ⚙️ Data Upload Strategy

- Load raw data into pandas DataFrames.
- Clean and transform data to match database schema.
- Use SQLAlchemy to insert data into relational tables.
- Manage duplicate checks to avoid redundant project records.

---

## 🔎 Query Example (Conceptual)

> **User Query:**
> “Find all costs for ‘PVC Pipe’ in Florida from 2022 to 2024.”

**Returned Results:**

| Item Description        | Unit | Unit Price | Project Name         | Project # | State | Year |
|-------------------------|------|------------|----------------------|-----------|-------|------|
| 8" PVC Gravity Sewer    | LF   | $45.32     | Main St. Sewer Rehab | 202301    | FL    | 2023 |

---

## 🧹 Data Maintenance & Purging

### Purging Old Data

- Admins can purge data older than a user-selected number of years.
- Optionally archive deleted records into CSVs before removal.
- Maintain logs of purging operations for audit trails.

### Workflow

1. Admin logs in.
2. Enters cutoff (e.g. delete data older than 5 years).
3. Clicks purge button.
4. System:
   - Deletes all items linked to old projects.
   - Deletes corresponding projects.
   - Confirms completion.

---

## 🔒 Security & Permissions

- Login system to control access.
- Admin-only routes for:
  - Data purging
  - User management
- Regular users can:
  - Search data
  - Export results

---

## 🚀 Design Approach & Development Steps

1. **Define Database Schema**
   - Design tables for projects, items, and users.

2. **Implement User Authentication**
   - User login
   - Admin vs regular user roles

3. **Develop Data Upload Module**
   - Build Python scripts to read Excel, CSV, or PDF.
   - Transform data for database insertion.

4. **Create API Endpoints**
   - Search queries
   - Data management

5. **Design Frontend UI**
   - Search form
   - Results table
   - Admin dashboard

6. **Build Data Purge Functionality**
   - Integrate into admin UI
   - Allow custom cutoff selection

7. **Testing & Validation**
   - Ensure query accuracy
   - Test purge functionality
   - Handle edge cases (e.g. duplicate entries)

8. **Deployment**
   - Host database (PostgreSQL locally or cloud)
   - Deploy app backend and frontend
   - Implement scheduled backups

---

## ✅ Benefits

- Saves significant time compared to manual searches.
- Provides a reliable data source for estimating and project planning.
- Improves transparency and traceability of cost estimates.
- Adds control over data growth and storage through purging.

---

## 📝 Future Enhancements

- Data visualization (e.g. cost trends over time).
- Statistical summaries (min, max, avg prices).
- Integration with mapping tools for geospatial visualization.
- Support for more file formats during upload.
- Notifications or reports for cost updates.

---

**TL;DR:**
This project will provide a powerful, searchable system for unit cost data in infrastructure projects, complete with secure admin controls and automated data maintenance. A perfect blend of Python, data engineering, and civil engineering knowledge—paving your way into fintech and beyond!
