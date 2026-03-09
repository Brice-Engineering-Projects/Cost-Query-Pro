# Cost Query Pro Database Schema

This document defines the database entities and relationships for the Cost Query Pro system.

---

## Authentication & Authorization

## users

| Field | Type | Notes |
| ----- | ----- | ----- |
| user_id | integer (PK) | Primary key |
| username | varchar(25) | |
| email | varchar(255) | |
| password_hash | text | |
| is_active | bool | |
| created_at | timestamp | |
| last_login | timestamp | |

---

## roles

| Field | Type | Notes |
| ----- | ----- | ----- |
| role_id | integer (PK) | |
| role_name | varchar(25) | |
| description | text | |

Example Roles:

- admin
- user

---

## permissions

| Field | Type | Notes |
| ----- | ----- | ----- |
| permissions_id | integer (PK) | |
| permission_name | varchar(25) | |
| description | text | |

Example Permissions:

- view_cost_data
- upload_projects
- manage_users
- purge_data
- export_data

---

## user_roles (many-to-many bridge)

| Field | Type | Notes |
| ----- | ----- | ----- |
| user_id | PK / FK | |
| role_id | PK / FK | |

---

## Geographic / Organizational Entities

## regions

| Field | Type | Notes |
| ----- | ----- | ----- |
| region_id | integer (PK) | |
| region_name | varchar(25) | |
| state | char(2) | |
| cost_index | numeric(5,2) | |

---

## agencies

| Field | Type | Notes |
| ----- | ----- | ----- |
| agency_id | integer (PK) | |
| agency_name | text | |
| state | char(2) | |
| city | text | |
| region_id | FK | |

Example Agencies:

- FDOT
- JEA
- Hillsborough County
- City of Tampa

---

## contractors

| Field | Type | Notes |
| ----- | ----- | ----- |
| contractor_id | integer (PK) | |
| contractor_name | text | |
| state | char(2) | |
| city | text | |
| is_prequalified | bool | |

---

## Project Classification Tables

## project_types

| Field | Type | Notes |
| ----- | ----- | ----- |
| project_type_id | integer (PK) | |
| type_name | varchar(25) | |

Examples:

- water
- sewer
- stormwater
- roadway
- site
- general

---

## project_size

| Field | Type | Notes |
| ----- | ----- | ----- |
| project_size_id | integer (PK) | |
| size_name | varchar(25) | |
| description | text | |

Example thresholds:

small: < $5M
medium: $5M–$25M
large: > $25M

---

## Core Project Data

## projects

| Field | Type |
| ----- | ----- |
| project_id | PK |
| project_name | text |
| project_number | text |
| agency_id | FK |
| region_id | FK |
| project_type_id | FK |
| bid_date | date |
| project_manager | varchar(255) |
| engineer_of_record | varchar(255) |
| construction_cost | numeric(14,2) |
| delivery_method | text |
| project_size_id | FK |

Delivery Method Examples:

- design_bid_build
- design_build
- cmar

---

## Cost Data Tables

## cost_items

| Field | Type | Notes |
| ----- | ----- | ----- |
| cost_item_id | PK | |
| pipe_use_id | FK | |
| canonical_description | text | |
| spec_section | varchar(15) | |
| material_type | varchar(25) | |
| material_spec | varchar(25) | |
| pipe_diameter | integer | |
| pressure_rating | varchar(15) | |
| item_category | varchar(50) | |
| installation_type | varchar(25) | |

Material Type Example:

PVC

Material Spec Examples:

- c900
- c905
- sch40
- sch80

Pressure Rating Examples:

- DR18
- DR25
- Class 350

Item Category Examples:

- Pipe
- Valve
- Manhole
- Pavement
- Concrete

---

## pipe_use

| Field | Type |
| ----- | ----- |
| pipe_use_id | integer (PK) |
| pipe_use_name | varchar(25) |
| description | text |

Examples:

- force_main
- gravity_sewer
- potable_water
- reclaimed_water
- storm_drain

---

## Units

## units

| Field | Type |
| ----- | ----- |
| unit_id | integer (PK) |
| unit_code | char(5) |
| unit_description | text |

Example Units:

- LF
- SY
- EA
- TON
- CY

---

## Bid Data

## bid_items

| Field | Type |
| ----- | ----- |
| bid_item_id | bigint (PK) |
| item_description | text |
| quantity | numeric(12,2) |
| unit_id | FK |
| unit_price | numeric(10,2) |
| project_id | FK |
| cost_item_id | FK |
| contractor_id | FK |
| created_at | timestamp |
| source_id | FK |

---

## Data Sources

## data_sources

| Field | Type |
| ----- | ----- |
| data_source_id | integer (PK) |
| source_name | varchar(25) |
| source_type | varchar(15) |
| file_name | text |
| upload_date | timestamp |
| processed_by | varchar(255) |

---

## Audit Logging

## audit_logs

| Field | Type |
| ----- | ----- |
| audit_id | bigint (PK) |
| user_id | FK |
| action | text |
| table_name | varchar(25) |
| record_id | FK |
| timestamp | timestamp |
| details_json | jsonb |
