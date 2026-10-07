from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RecipientInput(BaseModel):
    name: Optional[str] = Field(None, description="Full name of the certificate recipient")
    email: Optional[str] = Field(None, description="Email address of the recipient")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com"
            }
        }
    )


class JobCreateRequest(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=255, description="Name of the course, workshop, or event")
    issuer_name: str = Field("Global Tech Academy", min_length=2, max_length=255, description="Organization issuing the certificate")
    issue_date: Optional[str] = Field(None, description="Date formatted as YYYY-MM-DD or readable string. Defaults to today.")
    file_format: Optional[str] = Field("pdf", pattern="^(pdf|png)$", description="Certificate format: 'pdf' or 'png'")
    recipients: List[RecipientInput] = Field(..., min_length=1, description="List of recipients to generate certificates for")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_name": "Full Stack & Cloud Engineering Bootcamp",
                "issuer_name": "Global Tech Academy",
                "issue_date": "2026-10-07",
                "file_format": "pdf",
                "recipients": [
                    {"name": "Alice Johnson", "email": "alice@example.com"},
                    {"name": "Bob Smith", "email": "bob@example.com"},
                    {"name": "", "email": "invalid-email"}
                ]
            }
        }
    )


class CertificateResponse(BaseModel):
    id: str
    recipient_name: str
    recipient_email: Optional[str] = None
    status: str
    file_name: Optional[str] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    id: str
    event_name: str
    issuer_name: str
    issue_date: str
    file_format: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    download_all_url: Optional[str] = None
    certificates: List[CertificateResponse] = []

    model_config = ConfigDict(from_attributes=True)


class JobSummaryResponse(BaseModel):
    id: str
    event_name: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    status_url: str

    model_config = ConfigDict(from_attributes=True)
