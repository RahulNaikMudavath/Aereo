import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Certificate, JobStatus, CertificateStatus, utc_now
from app.schemas import JobCreateRequest, JobResponse, JobSummaryResponse, CertificateResponse
from app.services.job_processor import process_certificate_job

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=202)
def create_certificate_job(
    request_data: JobCreateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    sync: bool = Query(False, description="If true, processes synchronously before responding. Default is false (background async)."),
    db: Session = Depends(get_db)
):
    """
    Submits a batch certificate generation request.
    Validates payload and enqueues background processing.
    """
    if not request_data.recipients:
        raise HTTPException(status_code=400, detail="Recipient list cannot be empty.")

    job_id = str(uuid.uuid4())
    today_str = request_data.issue_date or datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Create the job
    job = Job(
        id=job_id,
        event_name=request_data.event_name.strip(),
        issuer_name=request_data.issuer_name.strip(),
        issue_date=today_str,
        file_format=request_data.file_format or "pdf",
        status=JobStatus.PENDING.value,
        total_count=len(request_data.recipients),
        success_count=0,
        failed_count=0,
        created_at=utc_now()
    )
    db.add(job)

    # Create placeholder certificate items for each recipient
    base_url = str(request.base_url).rstrip("/")
    for r in request_data.recipients:
        cert_id = str(uuid.uuid4())
        name = (r.name or "").strip()
        email = (r.email or "").strip() if r.email else None
        
        cert = Certificate(
            id=cert_id,
            job_id=job_id,
            recipient_name=name,
            recipient_email=email,
            status=CertificateStatus.PENDING.value,
            created_at=utc_now()
        )
        db.add(cert)

    db.commit()
    db.refresh(job)

    # Execute processing (synchronously or in background)
    if sync:
        process_certificate_job(job_id, db=db)
        db.refresh(job)
    else:
        background_tasks.add_task(process_certificate_job, job_id)

    # Build response
    return build_job_response(job, base_url)


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Retrieves the status, overall progress, and itemized results of a generation job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")

    base_url = str(request.base_url).rstrip("/")
    return build_job_response(job, base_url)


@router.get("/", response_model=List[JobSummaryResponse])
def list_jobs(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lists recent certificate generation jobs.
    """
    base_url = str(request.base_url).rstrip("/")
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    return [
        JobSummaryResponse(
            id=j.id,
            event_name=j.event_name,
            status=j.status,
            total_count=j.total_count,
            success_count=j.success_count,
            failed_count=j.failed_count,
            created_at=j.created_at,
            completed_at=j.completed_at,
            status_url=f"{base_url}/api/jobs/{j.id}"
        )
        for j in jobs
    ]


def build_job_response(job: Job, base_url: str) -> JobResponse:
    cert_responses = []
    has_successful_cert = False

    for c in job.certificates:
        download_url = None
        if c.status == CertificateStatus.COMPLETED.value:
            download_url = f"{base_url}/api/certificates/{c.id}/download"
            has_successful_cert = True

        cert_responses.append(
            CertificateResponse(
                id=c.id,
                recipient_name=c.recipient_name,
                recipient_email=c.recipient_email,
                status=c.status,
                file_name=c.file_name,
                error_message=c.error_message,
                download_url=download_url,
                created_at=c.created_at,
                completed_at=c.completed_at
            )
        )

    download_all_url = f"{base_url}/api/jobs/{job.id}/download-all" if has_successful_cert else None

    return JobResponse(
        id=job.id,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        file_format=job.file_format,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        download_all_url=download_all_url,
        certificates=cert_responses
    )
