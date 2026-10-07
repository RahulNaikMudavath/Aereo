# Bulk Certificate Generator API 🎓

A robust, production-ready backend service built with **Python**, **FastAPI**, **SQLAlchemy (SQLite)**, and **Pillow** designed to handle bulk certificate generation efficiently. It processes recipient batches asynchronously, isolates individual failures so that invalid rows never block valid certificates, tracks live job progress, and provides endpoints to retrieve certificates individually or as a `.zip` archive.

---

## 📑 Table of Contents
- [Key Features](#-key-features)
- [Architecture & Design](#-architecture--design)
- [Project Structure](#-project-structure)
- [Prerequisites & Installation](#-prerequisites--installation)
- [Running the Application](#-running-the-application)
- [Running the Test Suite](#-running-the-test-suite)
- [API Reference & Usage](#-api-reference--usage)
  - [1. Submit Certificate Generation Request](#1-submit-bulk-generation-request)
  - [2. Track Job Status & Progress](#2-track-job-status--progress)
  - [3. Download an Individual Certificate](#3-download-an-individual-certificate)
  - [4. Download All Certificates (.ZIP)](#4-download-all-certificates-as-zip)
  - [5. Public Certificate Verification](#5-public-certificate-verification)
- [Key Implementation & Design Decisions](#-key-implementation--design-decisions)
- [Future Scope & Production Scaling](#-future-scope--production-scaling)

---

## ✨ Key Features

1. **True Bulk Processing**: Accepts large batches of recipients in a single API call.
2. **Asynchronous Non-Blocking Processing**: Uses background tasks so API clients receive an immediate `202 Accepted` response with a polling status URL.
3. **Strict Failure Isolation**: If recipient #3 has an invalid email or missing name, it is recorded with an informative error message, while recipients #1, #2, and #4 are generated successfully.
4. **Relational Database Tracking**: Full job and certificate history stored with foreign key constraints, live progress counters (`total_count`, `success_count`, `failed_count`), and timestamps.
5. **High-Resolution Vector-Quality Certificates**: Generates A4 landscape certificates (1754 x 1240 px at 150 DPI) in either **PDF** or **PNG** with elegant double borders, seals, and typography.
6. **Bulk ZIP Retrieval**: Automatically packages all completed certificates into a `.zip` archive with clean sanitized filenames.
7. **Interactive Documentation**: Auto-generated Swagger UI (`/docs`) and ReDoc (`/redoc`).

---

## 🏛 Architecture & Design

```
+-------------------------------------------------------------------------------+
|                                 Client API                                    |
|   POST /api/jobs/  |  GET /api/jobs/{id}  |  GET /api/jobs/{id}/download-all  |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
                        +----------------------------+
                        |     FastAPI Web Server     |
                        |   - Request Validation     |
                        |   - Route Handlers         |
                        +----------------------------+
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        +---------------------+               +---------------------+
        |  SQLAlchemy Models  |               |  Background Worker  |
        |  - Job              |               |  - Item Validation  |
        |  - Certificate      |               |  - Pillow Renderer  |
        +---------------------+               |  - Failure Isolator |
                   │                          +---------------------+
                   ▼                                     │
        +---------------------+                          ▼
        |  Relational DB      |               +---------------------+
        |  (SQLite / Posgres) |               | Storage Directory   |
        +---------------------+               | - PDF / PNG files   |
                                              | - ZIP archives      |
                                              +---------------------+
```

---

## 📂 Project Structure

```
├── app/
│   ├── __init__.py
│   ├── config.py                  # Environment config and directory setup
│   ├── database.py                # Relational DB engine and session factory
│   ├── models.py                  # SQLAlchemy models (Job, Certificate)
│   ├── schemas.py                 # Pydantic validation schemas
│   ├── main.py                    # FastAPI application & middleware
│   ├── services/
│   │   ├── __init__.py
│   │   ├── certificate_generator.py # Pillow canvas rendering (PDF/PNG)
│   │   └── job_processor.py       # Batch processor with failure isolation
│   └── routers/
│       ├── __init__.py
│       ├── jobs.py                # Job submission, status, and listing endpoints
│       └── certificates.py        # Single/Bulk download & verification endpoints
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures and DB isolation
│   └── test_api.py                # Integration & unit test suite
├── storage/                       # Generated PDFs, PNGs, and ZIPs (auto-created)
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Pinned Python dependencies
├── .gitignore                     # Git ignore rules
└── README.md                      # Documentation
```

---

## 🚀 Prerequisites & Installation

### Prerequisites
- Python **3.10+** (Tested on Python 3.12, 3.13, 3.14)
- Git

### 1. Clone the Repository
```bash
git clone <your-repo-link>
cd "bulk-certificate-generator"
```

### 2. Set Up Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🖥 Running the Application

Start the development server with **Uvicorn**:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

Once running, access:
- **Interactive Swagger UI**: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc)
- **Health Check**: [http://127.0.0.1:8080/health](http://127.0.0.1:8080/health)

---

## 🧪 Running the Test Suite

Run the full automated test suite covering job creation, validation, failure handling, and downloads:

```bash
pytest -v
```

Output:
```
tests/test_api.py::test_health_check PASSED                              [ 11%]
tests/test_api.py::test_input_validation PASSED                          [ 22%]
tests/test_api.py::test_create_and_generate_certificates_asynchronously PASSED [ 33%]
tests/test_api.py::test_create_and_generate_certificates_synchronously PASSED [ 44%]
tests/test_api.py::test_job_status_endpoint PASSED                       [ 55%]
tests/test_api.py::test_individual_failure_isolation PASSED              [ 66%]
tests/test_api.py::test_download_individual_certificate PASSED           [ 77%]
tests/test_api.py::test_download_all_certificates_zip PASSED             [ 88%]
tests/test_api.py::test_verify_certificate_endpoint PASSED               [100%]

======================== 9 passed in 1.18s =========================
```

---

## 📡 API Reference & Usage

### 1. Submit Bulk Generation Request
- **Endpoint**: `POST /api/jobs/`
- **Query Params**:
  - `sync` (boolean, optional, default `false`): If `true`, waits for the entire batch to finish before responding. If `false`, immediately enqueues the job and returns `202 Accepted`.
- **Request Body**:
```json
{
  "event_name": "Full Stack & Cloud Engineering Masterclass",
  "issuer_name": "Global Tech Academy",
  "issue_date": "October 7, 2026",
  "file_format": "pdf",
  "recipients": [
    {
      "name": "Alice Johnson",
      "email": "alice@example.com"
    },
    {
      "name": "Bob Smith",
      "email": "bob@example.com"
    },
    {
      "name": "",
      "email": "invalid-recipient-without-name"
    }
  ]
}
```

- **Response (`202 Accepted`)**:
```json
{
  "id": "e2f7b8a1-c309-410a-8bf8-013346d2cb1e",
  "event_name": "Full Stack & Cloud Engineering Masterclass",
  "issuer_name": "Global Tech Academy",
  "issue_date": "October 7, 2026",
  "file_format": "pdf",
  "status": "PROCESSING",
  "total_count": 3,
  "success_count": 0,
  "failed_count": 0,
  "created_at": "2026-10-07T15:50:00Z",
  "completed_at": null,
  "download_all_url": null,
  "certificates": [
    {
      "id": "d09436fc-31ad-4673-90d5-bfb6df7d1a50",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "PENDING",
      "file_name": null,
      "error_message": null,
      "download_url": null,
      "created_at": "2026-10-07T15:50:00Z",
      "completed_at": null
    }
  ]
}
```

---

### 2. Track Job Status & Progress
- **Endpoint**: `GET /api/jobs/{job_id}`
- **Curl**:
```bash
curl -X GET "http://127.0.0.1:8080/api/jobs/e2f7b8a1-c309-410a-8bf8-013346d2cb1e"
```
- **Response (`200 OK`)**:
```json
{
  "id": "e2f7b8a1-c309-410a-8bf8-013346d2cb1e",
  "event_name": "Full Stack & Cloud Engineering Masterclass",
  "issuer_name": "Global Tech Academy",
  "issue_date": "October 7, 2026",
  "file_format": "pdf",
  "status": "PARTIALLY_COMPLETED",
  "total_count": 3,
  "success_count": 2,
  "failed_count": 1,
  "created_at": "2026-10-07T15:50:00Z",
  "completed_at": "2026-10-07T15:50:02Z",
  "download_all_url": "http://127.0.0.1:8080/api/jobs/e2f7b8a1-c309-410a-8bf8-013346d2cb1e/download-all",
  "certificates": [
    {
      "id": "d09436fc-31ad-4673-90d5-bfb6df7d1a50",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "COMPLETED",
      "file_name": "e2f7b8a1_d09436fc_Alice_Johnson.pdf",
      "error_message": null,
      "download_url": "http://127.0.0.1:8080/api/certificates/d09436fc-31ad-4673-90d5-bfb6df7d1a50/download",
      "created_at": "2026-10-07T15:50:00Z",
      "completed_at": "2026-10-07T15:50:01Z"
    },
    {
      "id": "a988dce5-1234-4a55-89cd-48ff2fbb4312",
      "recipient_name": "",
      "recipient_email": "invalid-recipient-without-name",
      "status": "FAILED",
      "file_name": null,
      "error_message": "Invalid Recipient: Name cannot be empty or whitespace.",
      "download_url": null,
      "created_at": "2026-10-07T15:50:00Z",
      "completed_at": "2026-10-07T15:50:02Z"
    }
  ]
}
```

---

### 3. Download an Individual Certificate
- **Endpoint**: `GET /api/certificates/{certificate_id}/download`
- **Curl**:
```bash
curl -O -J "http://127.0.0.1:8080/api/certificates/{certificate_id}/download"
```
Returns binary stream with headers:
- `Content-Type: application/pdf` or `image/png`
- `Content-Disposition: attachment; filename="<recipient_name>_certificate.pdf"`

---

### 4. Download All Certificates as ZIP
- **Endpoint**: `GET /api/jobs/{job_id}/download-all`
- **Curl**:
```bash
curl -O -J "http://127.0.0.1:8080/api/jobs/{job_id}/download-all"
```
Packages all successfully generated certificates in the job into a structured `.zip` file with sanitized names (`01_Alice_Johnson_certificate.pdf`, `02_Bob_Smith_certificate.pdf`, etc.).

---

### 5. Public Certificate Verification
- **Endpoint**: `GET /api/certificates/{certificate_id}/verify`
- **Response**:
```json
{
  "valid": true,
  "certificate_id": "d09436fc-31ad-4673-90d5-bfb6df7d1a50",
  "recipient_name": "Alice Johnson",
  "event_name": "Full Stack & Cloud Engineering Masterclass",
  "issuer_name": "Global Tech Academy",
  "issue_date": "October 7, 2026",
  "status": "COMPLETED",
  "completed_at": "2026-10-07T15:50:01Z"
}
```

---

## 💡 Key Implementation & Design Decisions

### 1. Framework: Why FastAPI?
- **Asynchronous Execution**: Native integration with Starlette's `BackgroundTasks` enables background job scheduling without requiring heavy infrastructure (like Redis/RabbitMQ) for local development and grading.
- **Type Safety & Auto-Validation**: Pydantic models automatically validate JSON payloads, schema limits, and types while generating interactive Swagger and ReDoc documentation.
- **Performance**: High throughput for I/O operations and file downloads.

### 2. Database: Why SQLite with SQLAlchemy?
- **Zero-Friction Relational Model**: Uses foreign keys, cascading deletes, indexes, and full ACID guarantees without requiring external database server installation.
- **Production Portability**: Switching to PostgreSQL or MySQL requires only changing the `DATABASE_URL` environment variable; the SQLAlchemy models and queries remain 100% unchanged.
- **Concurrency**: Configured with `connect_args={"check_same_thread": False}` to allow worker threads to update item progress seamlessly.

### 3. Asynchronous vs. Synchronous Processing
- **Default (Asynchronous `BackgroundTasks`)**: For batch sizes ranging from 10 to thousands of recipients, synchronous generation would cause HTTP client timeouts. Enqueuing work returns `202 Accepted` immediately, allowing clients to poll status or display progress bars.
- **Sync Option (`?sync=true`)**: Added for automated testing, internal scripting, or smaller single-certificate runs.

### 4. Failure Isolation Strategy
- Instead of rejecting an entire batch if one recipient is malformed, the validator evaluates each recipient independently inside a protected `try...except` block:
  - Valid recipients are generated and marked `COMPLETED`.
  - Faulty recipients are marked `FAILED` with an explicit reason (`Invalid Recipient: Name cannot be empty`).
  - The job status reflects this via granular states: `COMPLETED`, `PARTIALLY_COMPLETED`, or `FAILED`.

### 5. Certificate Engine: Why Pillow?
- **No Heavy C-Libraries**: Avoids native PDF library dependencies (like `weasyprint` / `wkhtmltopdf` / `cairo`) that frequently break across Windows, Mac, and Linux environments.
- **Vector-Grade Layout**: Renders crisp borders, gold geometric accents, centered typography, and authentic medallion seals.
- **Multi-Format Export**: Native support for exporting to both print-ready **PDF** and web-friendly **PNG** formats.

---

## 🔮 Future Scope & Production Scaling

If scaling this service to millions of certificates per month:
1. **Distributed Task Queue**: Replace FastAPI `BackgroundTasks` with **Celery** or **ARQ** backed by **Redis** or **RabbitMQ** across worker pools.
2. **Cloud Object Storage**: Transition from local `storage/` disk directory to **AWS S3** or **Google Cloud Storage (GCS)** using presigned download URLs.
3. **Webhooks & Email Delivery**: Emit webhook callbacks or trigger transactional emails (e.g., via SendGrid or AWS SES) delivering the certificate PDF to each recipient automatically.
4. **Dynamic Template Engine**: Support custom uploaded SVG or HTML templates with drag-and-drop placeholder coordinates.
