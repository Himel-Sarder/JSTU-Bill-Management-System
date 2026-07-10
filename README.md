<div align="center">

# JSTU Bill Management System

### Smart, role-based bill (ভাউচার) management system for the Department of CSE, Jamalpur Science and Technology University

[![Live Demo](https://img.shields.io/badge/Live%20Demo-jstu--exam--bill--management--system.onrender.com-2ea44f?style=for-the-badge&logo=render)](https://jstu-exam-bill-management-system.onrender.com/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge)](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-Framework-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/Dockerfile)

[Live Demo](https://jstu-exam-bill-management-system.onrender.com/) • [Report Bug](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/issues) • [Request Feature](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/issues) • [Security Policy](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/SECURITY.md)

</div>

---

## Preview

<p align="center">
  <img src="https://github.com/user-attachments/assets/87557a19-4577-4da5-8f55-74e2282ebd45" />
</p>
<p align="center">
  <img width="1763" height="3034" alt="image" src="https://github.com/user-attachments/assets/b76b4215-647b-4759-a956-335a4664b06f" />
</p>

---

## Table of Contents

- [About the Project](#about-the-project)
- [Key Features](#key-features)
- [User Roles](#user-roles)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Bill Lifecycle (Workflow)](#bill-lifecycle-workflow)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Installation](#local-installation)
  - [Environment Variables](#environment-variables)
  - [Bengali Font Setup](#bengali-font-setup)
- [Running with Docker](#running-with-docker)
- [Deployment (Render)](#deployment-render)
- [Core Routes / API Reference](#core-routes--api-reference)
- [Screenshots Gallery](#screenshots-gallery)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Author](#author)

---

## About the Project

**JSTU Bill Management System** is a full-stack web application built to digitize and streamline the process of creating, submitting, approving, and archiving **exam duty bills / vouchers (পরীক্ষার বিল)** for the Department of Computer Science & Engineering at **Jamalpur Science and Technology University (JSTU)**.

Previously, faculty members and staff had to manually calculate exam-duty payments (invigilation, script evaluation, question setting, etc.), fill out paper vouchers, and physically route them through the Chairman and Controller of Examinations for approval — a slow, error-prone, and hard-to-audit process.

This system replaces that workflow with:

- A **guided bill builder** where teachers pick a work type (e.g. *Invigilation*, *Script Evaluation*, *Question Setting*) and the system auto-calculates the amount based on configurable rules (fixed / per-piece / per-paper / per-question / per-hour / per-student / per-semester / per-person / per-day).
- A **multi-stage digital approval workflow** (Draft → Pending → Chairman Approval → Sent to Controller → Controller Approval → Paid), with rejection handling at every stage.
- **Auto-generated, print-ready PDF vouchers** in Bengali (বাংলা), complete with bill/voucher numbers, Bangla dates, bank details, and digital signatures.
- A **searchable dashboard**, Excel/PDF export, activity logging, and near real-time notification counters for admins and the Controller's office.

**Live Application:** https://jstu-exam-bill-management-system.onrender.com/
**Repository:** https://github.com/Himel-Sarder/JSTU-Bill-Management-System

---

## Key Features

### For Faculty / Staff (General Users)
- Role-aware registration & login (Chairman / Controller / Assistant Professor / Lecturer / Office Assistant)
- Dynamic bill builder — select **Work Type → Benefit/Sub-task → Quantity**, amount auto-calculated
- Degree-aware forms (Honours / Masters / Both) and semester selection (১ম–৮ম সেমিস্টার, মাস্টার্স)
- Bank detail capture (bank name, branch, account & routing numbers)
- Personal e-signature upload, embedded directly into the generated voucher
- One-click **PDF download & preview** of any bill, in Bengali typography
- "My Bills" history with live status badges (Draft, Pending, Approved, Rejected, Paid, Sent to Controller...)
- Edit / delete bills before they're finalized

### For Chairman / Office Assistant (Admins)
- Centralized **Dashboard** with bill statistics and quick filters
- **All Bills** view with advanced filtering (status, semester, degree, user, date range)
- Approve / reject bills with remarks, and forward approved bills to the Controller's office
- Manage up to **4 independent Chairman signature slots** (for signature rotation/succession) plus a general signature
- **Work Type & Benefit management** — configure calculation rules, base amounts, min/max units without touching code
- **User Management** — manage staff/faculty accounts and roles
- Bulk **export to PDF** of filtered bill lists
- **Activity Log** for full audit trail of every action

### For Controller of Examinations
- Dedicated **Controller inbox** for bills forwarded by the Chairman
- Approve / reject bills at the final stage, with automatic status propagation
- **Accepted / Rejected bill** views with PDF export
- Live **notification polling API** for incoming bill counts

### Platform-wide
- Bengali-first UI with Bangla digit/date conversion utilities
- Server-side PDF rendering via **WeasyPrint** with embedded Bengali fonts (Kalpurush / SolaimanLipi)
- Excel export support via **openpyxl**
- Media (signatures, slider images) stored on **Cloudinary**, decoupled from the app server
- Custom **Jazzmin**-themed Django admin panel (dark, teal accent, tabbed forms)
- Fully **Dockerized** with a one-command deployment to **Render**

---

## User Roles

| Role (বাংলা) | Role (English) | Typical Permissions |
|---|---|---|
| `চেয়ারম্যান` | Chairman (Dept. Head) | Approve/reject bills, manage signatures, forward to Controller, manage work types & users |
| `কন্ট্রোলার` | Controller of Examinations | Final approval/rejection of bills forwarded by the Chairman |
| `অফিস সহকারী` | Office Assistant | Admin-level dashboard & bill management support |
| `অ্যাসিস্ট্যান্ট প্রফেসর` | Assistant Professor | Create, edit, track own bills |
| `লেকচারার` | Lecturer | Create, edit, track own bills |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [Django](https://www.djangoproject.com/) (Python 3.11) |
| **Database** | PostgreSQL (via `dj-database-url` + `psycopg2-binary`), SQLite for local dev |
| **Admin Panel** | [django-jazzmin](https://github.com/farridav/django-jazzmin) (custom dark/teal theme) |
| **PDF Generation** | [WeasyPrint](https://weasyprint.org/) + custom Bengali fonts (Kalpurush, SolaimanLipi) |
| **Spreadsheet Export** | [openpyxl](https://openpyxl.readthedocs.io/) |
| **Media Storage** | [Cloudinary](https://cloudinary.com/) + `django-cloudinary-storage` |
| **Static Files** | [WhiteNoise](http://whitenoise.evans.io/) |
| **Image Processing** | [Pillow](https://python-pillow.org/) |
| **App Server** | [Gunicorn](https://gunicorn.org/) |
| **Containerization** | Docker |
| **Hosting** | [Render](https://render.com/) (`render.yaml` included) |
| **Frontend** | Django Templates + HTML/CSS (Bootstrap-style components), vanilla JS for dynamic forms & polling |

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client["Client (Browser)"]
        UI["Django Templates<br/>HTML / CSS / JS<br/>(base.html + core templates)"]
    end

    subgraph Server["Application Server — Gunicorn + Django"]
        direction TB
        URLS["URL Router<br/>bill_management.urls → core.urls"]
        VIEWS["core.views<br/>Auth, Bill CRUD, Workflow,<br/>Signature, Dashboard, API endpoints"]
        FORMS["core.forms<br/>BillForm, WorkTypeForm,<br/>BenefitForm, ProfileForm"]
        MODELS["core.models<br/>Bill, Task, WorkType, Benefit,<br/>Profile, ActivityLog, SystemSetting"]
        ADMIN["Django Admin + Jazzmin<br/>core.admin"]
        PDF["PDF Engine<br/>WeasyPrint + Bengali fonts"]
        EXCEL["Excel Export<br/>openpyxl"]
    end

    subgraph Data["Data Layer"]
        DB[("PostgreSQL / SQLite<br/>via dj-database-url")]
        CLOUD["Cloudinary<br/>Signatures & Slider Images"]
        STATIC["WhiteNoise<br/>Static Files (CSS/JS/Fonts)"]
    end

    UI -->|HTTPS Request| URLS
    URLS --> VIEWS
    VIEWS --> FORMS
    VIEWS --> MODELS
    VIEWS --> PDF
    VIEWS --> EXCEL
    ADMIN --> MODELS
    MODELS --> DB
    VIEWS -->|Upload/Fetch Media| CLOUD
    VIEWS -->|Serve Assets| STATIC
    PDF -->|Rendered Bill PDF| UI
    EXCEL -->|.xlsx Export| UI

    style Client fill:#1e293b,color:#fff,stroke:#38bdf8
    style Server fill:#0f172a,color:#fff,stroke:#22c55e
    style Data fill:#111827,color:#fff,stroke:#f59e0b
```

**Deployment topology:**

```mermaid
flowchart LR
    Dev["Developer<br/>git push"] --> GH["GitHub Repository"]
    GH -->|autoDeploy: true| Render["Render.com<br/>Docker Web Service"]
    Render --> Docker["Dockerfile<br/>Python 3.11 + WeasyPrint deps<br/>+ Bengali fonts"]
    Docker --> Gunicorn["Gunicorn<br/>bill_management.wsgi"]
    Gunicorn --> PG[("Render PostgreSQL<br/>bill_management_db")]
    Gunicorn --> CDN["Cloudinary CDN<br/>(media storage)"]
    Users["Faculty / Chairman / Controller"] -->|HTTPS| Render
```

---

## Bill Lifecycle (Workflow)

Every bill created in the system moves through a well-defined state machine (see `Bill.STATUS_CHOICES` in `core/models.py`):

```mermaid
stateDiagram-v2
    [*] --> Draft: Faculty creates bill
    Draft --> Pending: Submitted for review
    Pending --> Approved: Chairman approves
    Pending --> Rejected: Chairman rejects
    Approved --> SentToController: Chairman forwards bill
    SentToController --> ApprovedByController: Controller approves
    SentToController --> RejectedByController: Controller rejects
    ApprovedByController --> Paid: Payment processed
    Rejected --> [*]
    RejectedByController --> [*]
    Paid --> [*]

    note right of Draft
        Faculty can still edit/delete
        the bill at this stage
    end note
    note right of SentToController
        Bill becomes hidden from
        Chairman's active queue
    end note
```

| Status | Bengali Label | Meaning |
|---|---|---|
| `draft` | খসড়া | Bill saved but not yet submitted |
| `pending` | অপেক্ষমান | Awaiting Chairman's review |
| `approved` | অনুমোদিত | Approved by Chairman |
| `rejected` | বাতিল | Rejected by Chairman |
| `sent_to_controller` | কন্ট্রোলারে প্রেরিত | Forwarded to the Controller's office |
| `approved_by_controller` | কন্ট্রোলার কর্তৃক অনুমোদিত | Final approval by Controller |
| `rejected_by_controller` | কন্ট্রোলার কর্তৃক বাতিল | Final rejection by Controller |
| `paid` | পরিশোধিত | Payment disbursed |

---

## Database Schema

The repository ships a full ER diagram — view it here: [**Full Database Schema (image)**](https://github.com/user-attachments/assets/a9751f5c-1732-47da-aa57-a8aa755857cd)

<p align="center">
  <img src="https://github.com/user-attachments/assets/a9751f5c-1732-47da-aa57-a8aa755857cd" width="70%" alt="Database ER Diagram"/>
</p>

A simplified logical view of the core relationships:

```mermaid
erDiagram
    USER ||--o| PROFILE : has
    USER ||--o{ BILL : creates
    USER ||--o{ ACTIVITYLOG : performs
    WORKTYPE ||--o{ BENEFIT : contains
    BILL ||--o{ TASK : contains
    BILL }o--|| USER : "approved_by"
    BILL }o--|| USER : "controller_approved_by"

    PROFILE {
        string user_type
        image profile_picture
        string phone_number
        date joining_date
        image signature
        image signature_chairman1
        image signature_chairman2
        image signature_chairman3
        image signature_chairman4
    }

    WORKTYPE {
        string name
        string degree_type
        bool needs_benefit
        decimal default_amount
        bool is_active
    }

    BENEFIT {
        string name
        string calculation_type
        decimal base_amount
        string unit_label
        int min_unit
        int max_unit
    }

    BILL {
        string bill_number
        string voucher_number
        string semester
        string department
        string bangla_date
        decimal total_amount
        string status
        string degree_type
        datetime approved_at
        datetime sent_to_controller_at
        datetime controller_approved_at
    }

    TASK {
        string work_type
        string benefit
        int quantity
        string unit
        decimal amount
    }

    ACTIVITYLOG {
        string action
        string details
        string ip_address
        datetime created_at
    }
```

**Core models** (`core/models.py`):

| Model | Purpose |
|---|---|
| `Profile` | Extends Django's `User` with role, photo, phone, joining date, and up to 5 signature slots |
| `WorkType` | Master list of exam-duty categories (Invigilation, Script Evaluation, etc.), scoped by degree |
| `Benefit` | Sub-tasks under a `WorkType` with a configurable calculation strategy (fixed / per-unit) |
| `Bill` | The voucher itself — bank info, semester, status, approvals, timestamps |
| `Task` | Individual line-items that make up a `Bill`'s total amount |
| `SliderImage` | Homepage carousel content, managed via admin |
| `SystemSetting` | Generic key-value store for site-wide configuration |
| `ActivityLog` | Full audit trail — who did what, when, and from which IP |

---

## Project Structure

```
JSTU-Bill-Management-System/
├── bill_management/          # Django project root
│   ├── settings.py           # Core settings (DB, Cloudinary, Jazzmin, WeasyPrint config)
│   ├── urls.py                # Root URL conf (admin/ + core routes)
│   ├── wsgi.py / asgi.py
│
├── core/                      # Main application
│   ├── models.py              # Profile, WorkType, Benefit, Bill, Task, ActivityLog, SystemSetting
│   ├── views.py                # All business logic (auth, bill CRUD, workflow, PDF, APIs)
│   ├── forms.py                # Django ModelForms for bills, users, work types, benefits
│   ├── admin.py                 # Jazzmin-powered Django admin customization
│   ├── urls.py                  # App-level routes
│   ├── templatetags/            # Custom template filters (e.g. Bangla digit conversion)
│   └── migrations/              # DB schema history
│
├── templates/
│   ├── base.html                # Shared layout
│   ├── core/                    # Page templates (bill form, dashboard, PDF layout, etc.)
│   └── admin/                   # Custom admin overrides
│
├── static/
│   ├── css/                     # Custom stylesheets
│   ├── fonts/                   # Kalpurush / SolaimanLipi Bengali fonts (for WeasyPrint)
│   └── static/, admin/           # Third-party & admin static assets
│
├── media/                       # User-uploaded files (local dev only — prod uses Cloudinary)
│   ├── signatures/
│   └── slider_images/
│
├── Dockerfile                    # Production image (Python 3.11 + Pango/Cairo + fonts)
├── entrypoint.sh                 # Migrate + launch Gunicorn
├── render.yaml                   # Render.com service blueprint
├── download_fonts.py              # Helper to fetch Bengali TTF fonts
├── requirements.txt
├── manage.py
├── SECURITY.md
└── LICENSE                        # Apache-2.0
```

---

## Getting Started

### Prerequisites

- Python **3.11+**
- pip / virtualenv
- PostgreSQL (optional locally — SQLite works out of the box)
- System libraries for WeasyPrint (Cairo, Pango, GDK-Pixbuf) — see [WeasyPrint install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
- A free [Cloudinary](https://cloudinary.com/) account (for media storage)

### Local Installation

```bash
# 1. Clone the repository
git clone https://github.com/Himel-Sarder/JSTU-Bill-Management-System.git
cd JSTU-Bill-Management-System

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Download Bengali fonts required for PDF generation
python download_fonts.py

# 5. Configure environment variables (see table below)
cp .env.example .env             # create this file if it doesn't exist yet
# then edit .env with your own values

# 6. Apply database migrations
python manage.py makemigrations
python manage.py migrate

# 7. Create an admin (superuser) account
python manage.py createsuperuser

# 8. Collect static files (optional in dev, required before deployment)
python manage.py collectstatic --noinput

# 9. Run the development server
python manage.py runserver
```

The app will be available at **http://127.0.0.1:8000/** and the Django admin at **http://127.0.0.1:8000/admin/**.

### Environment Variables

The project reads its configuration from environment variables (see `bill_management/settings.py`). Set these locally in a `.env` file or export them in your shell:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | | Django secret key (auto-generated on Render) |
| `DEBUG` | | `True` for local dev, `False` in production |
| `DATABASE_URL` | | Full DB connection string, e.g. `postgres://user:pass@host:5432/dbname` (falls back to SQLite if unset locally) |
| `CLOUDINARY_CLOUD_NAME` | | Cloudinary account cloud name |
| `CLOUDINARY_API_KEY` | | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | | Cloudinary API secret |

> **Security note:** The `settings.py` in this repo currently ships with a hard-coded default `SECRET_KEY` and `DEBUG = True`. Before deploying to production, make sure to override both via environment variables and set `ALLOWED_HOSTS` to your actual domain.

### Bengali Font Setup

PDF bills are rendered server-side with **WeasyPrint**, which needs the Bengali fonts physically present on the system:

```bash
python download_fonts.py
```

This fetches `Kalpurush.ttf` and `SolaimanLipi.ttf` into `static/fonts/`. If the automatic download fails, grab them manually from [Omicronlab](https://www.omicronlab.com/bangla-fonts.html) or [Ekushey](https://www.ekushey.org/?page/fonts) and place them in the same folder. The Docker image also registers `kalpurush.ttf` system-wide via `fc-cache`.

---

## Running with Docker

The included [`Dockerfile`](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/Dockerfile) installs all native dependencies WeasyPrint needs (Cairo, Pango, GDK-Pixbuf) and pre-registers the Bengali fonts.

```bash
# Build the image
docker build -t jstu-bill-management .

# Run the container
docker run -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -e DEBUG="False" \
  -e DATABASE_URL="postgres://user:pass@host:5432/dbname" \
  -e CLOUDINARY_CLOUD_NAME="your-cloud-name" \
  -e CLOUDINARY_API_KEY="your-api-key" \
  -e CLOUDINARY_API_SECRET="your-api-secret" \
  jstu-bill-management
```

The container's [`entrypoint.sh`](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/entrypoint.sh) automatically runs migrations before starting Gunicorn:

```sh
python manage.py makemigrations
python manage.py migrate
exec gunicorn bill_management.wsgi:application --bind 0.0.0.0:$PORT --timeout 120
```

---

## Deployment (Render)

This project includes a ready-to-use [`render.yaml`](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/render.yaml) Blueprint for one-click deployment on [Render](https://render.com/):

1. Fork/clone this repository.
2. On Render, choose **New → Blueprint** and point it at your repo.
3. Render will provision:
   - A **Docker web service** (`bill-management`) built from the included `Dockerfile`
   - A managed **PostgreSQL** database (`bill_management_db`), auto-wired via `DATABASE_URL`
   - An auto-generated `SECRET_KEY`
4. Add the Cloudinary secrets (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`) manually in the Render dashboard's Environment tab.
5. Push to `main` — `autoDeploy: true` means every push redeploys automatically.

**Currently live at:** https://jstu-exam-bill-management-system.onrender.com/

---

## Core Routes / API Reference

A selection of the most important routes from `core/urls.py`:

| Route | Purpose |
|---|---|
| `/` | Home — role-aware landing page (redirects Controller to their inbox) |
| `/login/`, `/logout/`, `/register/` | Authentication |
| `/profile/` | View/update own profile |
| `/bill/create/` | Create a new bill |
| `/my-bills/` | Faculty's own bill history |
| `/bill/edit/<id>/`, `/bill/delete/<id>/` | Edit / delete a bill |
| `/bill/download/<id>/`, `/bill/view/<id>/` | Download / preview bill as PDF |
| `/bill-status/` | Status overview |
| `/send-bill/<id>/`, `/bill/send-to-controller/<id>/` | Advance a bill through the workflow |
| `/dashboard/` | Admin dashboard |
| `/all-bills/`, `/all-bills/export-pdf/` | Full bill listing + bulk PDF export |
| `/bill/update-status/<id>/` | Chairman approve/reject |
| `/user-management/` | Manage faculty/staff accounts |
| `/dashboard/work-types/`, `/dashboard/benefits/` | Configure work types & benefits |
| `/signature-upload/general/`, `/signature-upload/chairman{1-4}/` | Manage e-signatures |
| `/bills/` (Controller), `/accepted-bills/`, `/rejected-bills/` | Controller's bill queues |
| `/controller/update-bill-status/<id>/` | Controller approve/reject |
| `/api/bill-counts/` | JSON — live notification counters |
| `/api/mark-notification-seen/` | Mark notifications as read |
| `/get-work-types/`, `/get-benefit-choices/`, `/get-work-type-amount/` | AJAX endpoints powering the dynamic bill form |
| `/admin/` | Django Admin (Jazzmin theme) |

---

## Screenshots Gallery

| Home / Bill Form | Admin Dashboard | Generated PDF |
|---|---|---|
| <img width="300" alt="Home" src="https://github.com/user-attachments/assets/9ad6ec0a-1f29-4491-a897-c5bcad8a28e5" /> | <img width="300" alt="Admin Dashboard" src="https://github.com/user-attachments/assets/5155f207-9998-441d-8227-962c97175523" /> | <img width="300" alt="PDF" src="https://github.com/user-attachments/assets/8213c705-3236-4abf-b388-e4cc2de7d469" /> |

---

## Roadmap

- [] REST API layer for mobile clients
- [] Email/SMS notifications on status change
- [] Multi-department support (beyond CSE)
- [] Bulk bill import via Excel
- [] Automated test coverage (`core/tests.py` currently minimal)
- [] Role-based two-factor authentication

Have an idea? [Open a feature request](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/issues)

---

## Contributing

Contributions make the open-source community amazing — any contribution is **greatly appreciated**.

1. [Fork the repository](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/fork)
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m "Add: AmazingFeature"`
4. Push to the branch: `git push origin feature/AmazingFeature`
5. [Open a Pull Request](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/pulls)

Please open an issue first for major changes so we can discuss what you'd like to change.

---

## Security

If you discover a security vulnerability, please **do not** open a public issue. Refer to the project's [**Security Policy**](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/SECURITY.md) for supported versions and responsible-disclosure guidance.

---

## License

Distributed under the **Apache License 2.0**. See [`LICENSE`](https://github.com/Himel-Sarder/JSTU-Bill-Management-System/blob/main/LICENSE) for full details.

---

## Author

**Himel Sarder**
Dept. of Computer Science and Engineering, Jamalpur Science and Technology University

[![GitHub](https://img.shields.io/badge/GitHub-Himel--Sarder-181717?style=flat&logo=github)](https://github.com/Himel-Sarder)

---

<div align="center">

**If this project helped you, consider giving it a star on GitHub!**

[Back to Top](#jstu-bill-management-system)

</div>
