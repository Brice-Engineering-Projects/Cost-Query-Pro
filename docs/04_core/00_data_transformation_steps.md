# 🚀 Next Development Phase — Data Upload & Transformation Module

## 🧬 Context

You’ve completed **authentication** — the foundation of the Cost Query Pro backend.
The next milestone is to enable **data ingestion** from bid tab files (CSV, Excel, PDF),
transform them into clean tabular form, and store them in the **PostgreSQL** database.

This is the heart of the system — everything else (search, purge, analytics) depends on it.

---

## 🌟 Goal

Implement a **Data Upload & Transformation Pipeline** that allows authenticated users
(admins in particular) to upload bid tab data for ingestion.

The pipeline should:

1. Parse and clean uploaded files (`CSV`, `Excel`, or later `PDF`).
2. Validate and normalize project and item data.
3. Insert records into the `projects` and `items` tables.
4. Log operations for traceability.

---

## 🧱 Implementation Phases

### **1. Model Layer (`app/models/`)**

Define SQLAlchemy ORM models:

**`Project` model**

* `id`: int, primary key
* `project_name`: str
* `project_number`: str (unique)
* `state`: str (2-char)
* `year`: int
* Relationship → `items`

**`Item` model**

* `id`: int, primary key
* `project_id`: FK → `projects.id`
* `item_description`: str
* `unit`: str
* `unit_price`: Decimal(12, 2)

Example:

```python
# app/models/project.py
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    project_name = Column(Text, nullable=False)
    project_number = Column(Text, unique=True, nullable=False)
    state = Column(String(2), nullable=False)
    year = Column(Integer, CheckConstraint("year > 1900"))
    items = relationship("Item", back_populates="project", cascade="all, delete")
```

---

### **2. Schema Layer (`app/schemas/`)**

Define Pydantic models to validate incoming and outgoing data.

```python
class ProjectCreate(BaseModel):
    project_name: str
    project_number: str
    state: str
    year: int

class ItemCreate(BaseModel):
    project_id: int
    item_description: str
    unit: str
    unit_price: Decimal
```

---

### **3. Core Logic (`app/core/data_upload.py`)**

Implement the ETL logic using pandas and SQLAlchemy.

**Responsibilities:**

* Detect file type (`.csv`, `.xlsx`, `.pdf`)
* Read into a DataFrame
* Clean and standardize column names
* Drop duplicates
* Insert data via session

Example structure:

```python
def process_upload(file_path: str, db: Session) -> dict:
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(file_path)
    elif ext in [".xls", ".xlsx"]:
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format")

    # Normalize column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Insert projects/items into DB
    ...
    return {"records_inserted": len(df)}
```

---

### **4. Route Layer (`app/api/projects.py`)**

Implement the `/api/v1/projects/upload` endpoint.

```python
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admins only")

    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    result = process_upload(temp_path, db)
    return {"message": "File processed successfully", **result}
```

_**Headers**_

```json
{
Authorization: Bearer <JWT>
Content-Type: multipart/form-data
}
```

---

### **5. Error Handling & Logging**

* Reject unsupported file types with `HTTP 400`.
* Log all upload activity in `cost_query_pro.log` using the logger configured in `settings.py`.
* Include details: username, filename, record count, timestamp.

---

## 🔎 Step After Upload: Search API

Once uploads are working and DB is populated:

1. Implement `/api/v1/items/search` (query by `q`, `state`, `year_start`, `year_end`).
2. Join `projects` + `items` tables and return results as JSON.
3. Add pagination for large result sets.

---

## 🔐 Optional Next: Admin Tools

* **Data Purging** — `/admin/purge` to delete records before a cutoff year.
* **User Management** — `/admin/users` for list and delete operations.

---

## 🧭 Immediate Deliverable

Focus on completing the **Data Upload Module** with:

* CSV and Excel support
* Admin restriction
* Logging and validation
* Database insert confirmation

---

## ✅ Summary Roadmap

| Phase | Feature     | Goal                                               |
| ----- | ----------- | -------------------------------------------------- |
| 1     | Data Upload | Enable admins to upload and parse cost data        |
| 2     | Search API  | Allow users to query items by term, state, year    |
| 3     | Admin Tools | Data purge + user management                       |
| 4     | Frontend    | Build simple dashboard for search/upload           |
| 5     | Deployment  | Prepare production configs (Postgres + AWS/Heroku) |

---

**TL;DR:**
You’ve got auth locked down.
Next — give the app its data heartbeat: the **upload engine** that turns PDFs and spreadsheets into a structured, queryable cost database.
