import os
import zipfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import ZIPS_DIR
from app.database import get_db
from app.models import Job, Certificate, CertificateStatus

router = APIRouter(tags=["Certificates"])


@router.get("/api/certificates/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Downloads a single generated certificate file (PDF or PNG).
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")

    if cert.status != CertificateStatus.COMPLETED.value or not cert.file_path:
        raise HTTPException(
            status_code=400,
            detail=f"Certificate is not ready for download. Current status: '{cert.status}'. Error: {cert.error_message}"
        )

    file_path = Path(cert.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found on disk.")

    media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "image/png"
    return FileResponse(
        path=file_path,
        filename=cert.file_name or file_path.name,
        media_type=media_type
    )


@router.get("/api/jobs/{job_id}/download-all")
def download_all_certificates(job_id: str, db: Session = Depends(get_db)):
    """
    Packages and downloads all successfully generated certificates in a job as a single .ZIP archive.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    completed_certs = [
        c for c in job.certificates
        if c.status == CertificateStatus.COMPLETED.value and c.file_path and Path(c.file_path).exists()
    ]

    if not completed_certs:
        raise HTTPException(
            status_code=400,
            detail=f"No generated certificates available to download for this job. (Job status: '{job.status}')"
        )

    # Prepare ZIP file
    safe_event_name = "".join(c if c.isalnum() else "_" for c in job.event_name.strip())
    zip_filename = f"{safe_event_name}_{job.id[:8]}_certificates.zip"
    zip_path = ZIPS_DIR / f"{job.id}.zip"

    # Always recreate or update zip to reflect latest completed certificates
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for idx, cert in enumerate(completed_certs, start=1):
            file_path = Path(cert.file_path)
            clean_recipient = "".join(c if c.isalnum() else "_" for c in cert.recipient_name.strip())
            archive_name = f"{idx:02d}_{clean_recipient}_certificate{file_path.suffix}"
            zipf.write(file_path, arcname=archive_name)

    return FileResponse(
        path=zip_path,
        filename=zip_filename,
        media_type="application/zip"
    )


@router.get("/api/certificates/{certificate_id}/verify")
def verify_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Public verification endpoint to authenticate a certificate by its unique ID.
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        return {
            "valid": False,
            "message": "Certificate ID is invalid or does not exist."
        }

    if cert.status != CertificateStatus.COMPLETED.value:
        return {
            "valid": False,
            "status": cert.status,
            "message": f"Certificate generation has not completed or failed. Error: {cert.error_message}"
        }

    return {
        "valid": True,
        "certificate_id": cert.id,
        "recipient_name": cert.recipient_name,
        "event_name": cert.job.event_name,
        "issuer_name": cert.job.issuer_name,
        "issue_date": cert.job.issue_date,
        "status": cert.status,
        "completed_at": cert.completed_at
    }
