import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.config import CERTIFICATES_DIR
from app.database import SessionLocal
from app.models import Job, Certificate, JobStatus, CertificateStatus, utc_now
from app.services.certificate_generator import generate_certificate_file

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_recipient(name: str, email: Optional[str]) -> None:
    """
    Validates recipient information.
    Raises ValueError with a clear user-facing error message if validation fails.
    """
    if not name or not isinstance(name, str) or not name.strip():
        raise ValueError("Invalid Recipient: Name cannot be empty or whitespace.")

    if len(name.strip()) < 2:
        raise ValueError("Invalid Recipient: Name must be at least 2 characters long.")

    if email:
        cleaned_email = email.strip()
        if not EMAIL_REGEX.match(cleaned_email):
            raise ValueError(f"Invalid Recipient: '{email}' is not a valid email address.")


def process_certificate_job(job_id: str, db: Optional[Session] = None) -> None:
    """
    Asynchronous or synchronous job execution worker.
    Processes each recipient in the job with strict failure isolation:
    a failure on one certificate will NOT fail the rest of the job.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job with ID '{job_id}' not found.")
            return

        job.status = JobStatus.PROCESSING.value
        db.commit()

        certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()
        
        success_count = 0
        failed_count = 0

        for cert in certificates:
            try:
                # 1. Validation phase
                validate_recipient(cert.recipient_name, cert.recipient_email)

                # 2. Certificate rendering phase
                safe_name = "".join(c if c.isalnum() else "_" for c in cert.recipient_name.strip())
                file_stem = f"{job.id[:8]}_{cert.id[:8]}_{safe_name}"
                target_path = CERTIFICATES_DIR / f"{file_stem}.{job.file_format}"

                generated_file = generate_certificate_file(
                    recipient_name=cert.recipient_name.strip(),
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    certificate_id=cert.id,
                    output_path=target_path,
                    file_format=job.file_format
                )

                # 3. Mark success
                cert.status = CertificateStatus.COMPLETED.value
                cert.file_path = str(generated_file.resolve())
                cert.file_name = generated_file.name
                cert.error_message = None
                cert.completed_at = utc_now()
                success_count += 1

            except Exception as exc:
                # 4. Isolated failure handling
                logger.warning(f"Failed to generate certificate for '{cert.recipient_name}': {exc}")
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = str(exc)
                cert.completed_at = utc_now()
                failed_count += 1

            # Update live counter and commit per item to allow real-time progress tracking
            job.success_count = success_count
            job.failed_count = failed_count
            db.commit()

        # Finalize job status
        if success_count == job.total_count:
            job.status = JobStatus.COMPLETED.value
        elif success_count > 0:
            job.status = JobStatus.PARTIALLY_COMPLETED.value
        else:
            job.status = JobStatus.FAILED.value

        job.completed_at = utc_now()
        db.commit()

    except Exception as exc:
        logger.error(f"Critical error processing job {job_id}: {exc}", exc_info=True)
        if job:
            job.status = JobStatus.FAILED.value
            db.commit()
    finally:
        if should_close_db:
            db.close()
