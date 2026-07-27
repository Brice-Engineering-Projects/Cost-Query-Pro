
# Cost Query Pro — Developer Diary Logs

**Last Updated:** 2026-07-26
**Maintainer:** Brice Nelson, P.E., MBA
**Project:** Cost Query Pro (FastAPI + PostgreSQL + Alembic)

---

## 📘 Purpose

This directory contains the full developer diary for Cost Query Pro,
split by functional areas and enhanced with metadata and auto-generated tags.

Each log includes the full narrative, code snippets, and engineering decisions
exactly as recorded.

---

## 🗂️ Folder Overview

Entries are grouped by project phase. Within a phase, subfolders use a shared
topic numbering (`01` auth, `02` ci_cd, `03` schema, `04` debugging_sessions,
`05` ai_agent) so the same topic keeps the same number across phases.

| Folder            | Description                                                                  |
| ----------------- | ------------------------------------------------------------------------------ |
| 00_general        | Cross-phase material that is not tied to one phase — currently CI/CD.        |
| 01_phase_1        | Phase 1: auth, schema and migrations, debugging sessions, ingestion pipeline. |
| 02_phase_2        | Phase 2: AI agent, cost control, admin operations.                           |
| 99_future_tasks   | Consolidated checklist and to-do items.                                      |

Supporting files: [`index.md`](./index.md) is the entry index,
[`diary_log_structure.md`](./diary_log_structure.md) documents the intended
layout, and [`diary_log.md`](./diary_log.md) is the original combined log the
split entries were extracted from.

---

## 🧩 Metadata Format

Each diary file begins with a YAML header for filtering and indexing:

```yaml
---
title: Cost Query Pro — Example Entry
date: 2025-09-08
tags: [ci_cd, fastapi, postgres]
---
```

---

## 🕒 Changelog

| Date       | Description                                                                                      |
| ---------- | -------------------------------------------------------------------------------------------------- |
| 2025-10-12 | Automated diary parsing and export completed.                                                    |
| 2026-07-26 | Rebuilt `index.md` and this folder table against the phase-based layout; both had been written against the earlier flat structure and every link was broken. Added the first Phase 2 entry. |

---

*Originally generated from `diary_log.md`; maintained by hand since the move to
phase-based folders.*
