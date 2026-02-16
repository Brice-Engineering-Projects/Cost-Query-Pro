# Business Scope Document

---

## Project Title

_**Unit Cost Query App for Infrastructure Projects**_

---

## 1. Executive Summary

In the world of municipal and infrastructure construction, historical unit costs—like those for pipes, paving, or manholes—are pure gold. Yet this “gold” is scattered across a digital mess of bid tabulations, PDFs, and Excel sheets.

Estimators, engineers, and analysts waste precious time digging through documents instead of focusing on strategic planning or accurate budgeting.

The **Unit Cost Query App** will centralize and streamline access to historical cost data, allowing users to quickly:

- Search for specific items (e.g. “PVC pipe”)
- Filter by location and year
- Retrieve detailed cost results including project context

This tool promises to save countless hours, increase estimating accuracy, and modernize how infrastructure professionals handle cost data.

---

## 2. Problem Statement

Current pain points in the industry include:

- Historical unit cost data is **scattered and inconsistent** across PDFs, Excel files, and bid tabulations.
- Locating cost information is **manual and time-consuming**.
- Lack of a centralized, queryable system impedes fast and data-driven decision-making.

**Business Opportunity:**

Provide a reliable, fast, and user-friendly system that empowers infrastructure professionals to instantly access historical cost information for better estimates and project planning.

---

## 3. Project Goals & Objectives

**Primary Goal:**

Develop an application to **search unit costs by item, state, and year**, returning relevant pricing data and project details.

**Key Objectives:**

- Centralize cost data into a secure, organized database.
- Provide intuitive search tools with filtering capabilities.
- Enable administrators to manage data, users, and system health.
- Ensure high performance, data integrity, and scalability.

---

## 4. Project Scope

### Core Functionalities

✅ **Data Upload Module**

- Import bid tab data from:
  - Excel
  - CSV
  - PDF (using PDF extraction tools)

✅ **Search & Query Engine**

- Search for item descriptions via keyword
- Filter results by:
  - State
  - Year range
- Display:
  - Item description
  - Unit
  - Unit price
  - Project name
  - Project number
  - State
  - Year

✅ **User Management & Security**

- Secure login system
- Role-based access:
  - Admins can manage users and data purging
  - Regular users can search and export data

✅ **Data Maintenance**

- Purge or archive outdated data
- Maintain logs for audit and compliance

---

## 5. Out of Scope (Initial Phase)

- Predictive pricing models
- Complex analytics dashboards
- Integration with external estimating software
- Real-time public data scraping
- Detailed GIS mapping visualizations

_*(But hey, we’ll get there one day!)*_

---

## 6. Technical Architecture

### Backend

- Python
- FastAPI framework
- SQLAlchemy ORM

### Database

- PostgreSQL for relational storage
- SQLAlchemy for DB interactions

### Frontend

Options:

- Jinja2 templates for a classic web UI
- Or modern frameworks like:
  - React
  - Vue
  - Streamlit (great for rapid prototypes)

### Data Tools

- pandas for ETL (extract-transform-load) processes
- pdfplumber or tabula-py for PDF table extraction

---

## 7. Database Design (High Level)

### Projects Table

- Project ID
- Project Name
- Project Number
- State
- Year

### Items Table

- Item ID
- Project ID (FK)
- Item Description
- Unit
- Unit Price

### Users Table

- User ID
- Username
- Password Hash
- Is_Admin (flag)

**Relationships:**

- One project → many items.

---

## 8. Data Upload & Transformation Process

- Raw data imported into pandas DataFrames.
- Data cleaned and standardized.
- Checks for duplicate projects.
- Data loaded into relational tables via SQLAlchemy.

---

## 9. Sample Query Scenario

> **User Query:**
> “Show me all costs for ‘PVC Pipe’ in Florida from 2022 to 2024.”

**Example Result:**

| Item Description     | Unit | Unit Price | Project Name         | Project # | State | Year |
| -------------------- | ---- | ---------- | -------------------- | --------- | ----- | ---- |
| 8" PVC Gravity Sewer | LF   | $45.32     | Main St. Sewer Rehab | 202301    | FL    | 2023 |

---

## 10. Security & Access Controls

- User authentication (username/password)
- Secure password hashing
- Admin-only routes for:
  - User management
  - Data purging
- Regular users can:
  - Search data
  - Export results

---

## 11. Data Maintenance

### Purging Process

- Admin selects cutoff year.
- System deletes items linked to outdated projects.
- Deletes associated projects.
- Archives data to CSV if desired.
- Logs operation for records.

---

## 12. Development Plan

### Phases

1. **Design DB Schema**
   - Define tables and relationships.

2. **Authentication Module**
   - User login
   - Admin privileges

3. **Data Upload Engine**
   - Scripts for file ingestion and transformation

4. **API Development**
   - Endpoints for search, uploads, admin actions

5. **Frontend Development**
   - Search UI
   - Admin dashboard

6. **Data Purge Functionality**
   - Build purge interface
   - Connect to backend logic

7. **Testing & QA**
   - Validate search results
   - Check security
   - Test purging operations

8. **Deployment**
   - Host backend & database
   - Deploy frontend
   - Set up backups

---

## 13. Benefits & Business Value

- Reduces time spent manually searching for cost data.
- Improves estimating accuracy and reliability.
- Supports transparent project planning.
- Allows proactive data management and storage efficiency.

---

## 14. Future Enhancements

- Cost trends visualization.
- Statistical summaries (min, max, avg).
- Geospatial visualizations.
- Expanded file format support (e.g. XML, JSON).
- Automated notifications or cost change alerts.

---

## 15. Risks & Considerations

- Data quality varies greatly across bid tab sources.
- PDF extraction can be inconsistent depending on formatting.
- Ensuring a clean, user-friendly UI is crucial for adoption.
- Security must protect sensitive cost and project data.

---

## 16. Success Metrics

- Time reduction in cost data searches
- Number of projects successfully imported
- User adoption rates
- Accuracy of search results
- System performance under load

---

## TL;DR

The **Unit Cost Query App** will revolutionize how civil and infrastructure professionals access historical cost data—turning scattered files into an organized, searchable goldmine. More speed. Less headache. Future-ready.
