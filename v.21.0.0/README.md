# School Management System (SMS) — Advanced Relational Desktop Suite

An enterprise-grade, multi-tenant desktop application designed to fully automate and manage an educational institution's administrative, financial, operational, and academic workflows. This project utilizes a **Three-Tier Software Architecture** featuring an object-oriented Python 3.x Tkinter user interface backed by a highly optimized, fully normalized MySQL relational database server.

---

## 🛠 Project Metadata & Context

* **Software Build Version:** `v.21.0.0` *(Initial Stable Build — `21` denotes the lifecycle creation year)*
* **Development Timeline:**
    * **Project Initiation:** November 2021
    * **Project Completion & Freeze:** February 2022
* **Development & Design Team (Authors):**
    * Varun Kumar
    * Shrishti Yadav
    * *and Group Members*
* **Target Submissions:** Class XII Board Computer Science (Subject Code: 083) Capstone Project

---

## 📂 System Architecture & File Registry

The system follows a modular architecture separating the Presentation Layer (UI layout & controls), Business Logic Layer (operations, computations, and validations), and Data Access Layer (database queries & transactions).

```text
SchoolManagementSystem/
│
├── data/
│   └── database_backup.sql       # Pre-indexed DDL table initialization and evaluation mock data
│
├── docs/
│   ├── Project_Synopsis.pdf     # Executive project synopsis and hardware metrics
│   └── Project_Report.pdf       # Formal board-compliant project file with verification logs
│
├── src/                          # Application source environment
│   ├── main.py                   # Master driver engine; manages Tkinter frames and authentication cycles
│   ├── utils.py                  # Standard styling guides, visual themes, trees, and form factories
│   ├── db_config.py              # Centralized data pool connectors and auto-seeding logic
│   ├── auth.py                   # Secure role validation (ACL) and SHA-256 password crypt-hashing
│   ├── student.py                # Registration desks, approval queues, and automatic pass/fail promotions
│   ├── employee.py               # HR profiles, staff indexing matrices, and course faculty mappings
│   ├── attendance.py             # Calendar monitoring grids and simulated parent absentee warnings
│   ├── exams.py                  # Grade-boundary builders, score sheets, and report card generators
│   ├── finance.py                # Institutional accounting heads, spending ledgers, and billing invoices
│   ├── library.py                # Asset indexing, checkout monitors, and automated cumulative delay fines
│   └── reports.py                # Comprehensive data-driven analytics engine running complex SQL reporting
│
└── requirements.txt              # Unified external software runtime dependencies manifest
